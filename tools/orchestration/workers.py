#!/usr/bin/env python3
"""Worker discovery, persistence, and inspection helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.history import list_aggregate_events
from tools.orchestration.interventions import intervention_blocking_condition, intervention_next_action
from tools.orchestration.session import build_paths
from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction


DISCOVERABLE_WORKER_STATES = {"ready", "busy", "degraded"}
MANUAL_DISABLE_TAG = "manual_disabled"
RUNTIME_DEFAULT_CAPABILITIES = {
    "codex": ["implementation", "review", "solutioning"],
    "claude": ["analysis", "planning", "solutioning", "review"],
    "gemini": ["planning", "solutioning", "implementation"],
    "local": ["privacy_sensitive", "documentation", "analysis"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class DiscoveredWorker:
    worker_id: str
    runtime_type: str
    adapter_id: str
    tmux_socket: str
    tmux_session: str
    tmux_pane: str
    state: str
    capabilities: list[str]
    required_signal_status: str
    last_evidence_at: str
    last_heartbeat_at: str
    interruptibility: str
    operator_tags: list[str]
    window_name: str
    pane_title: str
    pane_current_command: str

    def as_dict(self) -> dict[str, object]:
        return {
            "worker_id": self.worker_id,
            "runtime_type": self.runtime_type,
            "adapter_id": self.adapter_id,
            "tmux_socket": self.tmux_socket,
            "tmux_session": self.tmux_session,
            "tmux_pane": self.tmux_pane,
            "state": self.state,
            "capabilities": self.capabilities,
            "required_signal_status": self.required_signal_status,
            "last_evidence_at": self.last_evidence_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "interruptibility": self.interruptibility,
            "operator_tags": self.operator_tags,
            "window_name": self.window_name,
            "pane_title": self.pane_title,
            "pane_current_command": self.pane_current_command,
        }


class WorkerNotFoundError(RuntimeError):
    """Raised when a requested worker does not exist."""


def discover_tmux_workers(
    repo_root: Path,
    *,
    tmux_socket: str | None = None,
    tmux_session: str | None = None,
    observed_at: str | None = None,
) -> list[DiscoveredWorker]:
    socket, session = resolve_tmux_context(repo_root, tmux_socket=tmux_socket, tmux_session=tmux_session)
    if not _socket_is_live(socket):
        return []
    observed_at = observed_at or utc_now()
    listing = _tmux(
        socket,
        [
            "list-panes",
            "-a",
            "-F",
            "#{session_name}\t#{window_name}\t#{pane_id}\t#{pane_title}\t#{pane_current_command}\t#{pane_active}",
        ],
    )
    workers: list[DiscoveredWorker] = []
    for raw_line in listing.splitlines():
        if not raw_line.strip():
            continue
        session_name, window_name, pane_id, pane_title, pane_current_command, pane_active = raw_line.split(
            "\t", 5
        )
        if session_name != session:
            continue
        runtime_type = infer_runtime_type(window_name, pane_title, pane_current_command)
        state = "busy" if pane_active == "1" and pane_current_command not in {"bash", "zsh", "fish"} else "ready"
        workers.append(
            DiscoveredWorker(
                worker_id=build_worker_id(runtime_type, session_name, pane_id),
                runtime_type=runtime_type,
                adapter_id=runtime_type,
                tmux_socket=socket,
                tmux_session=session_name,
                tmux_pane=pane_id,
                state=state,
                capabilities=RUNTIME_DEFAULT_CAPABILITIES[runtime_type],
                required_signal_status="required_only",
                last_evidence_at=observed_at,
                last_heartbeat_at=observed_at,
                interruptibility="interruptible",
                operator_tags=["discovered"],
                window_name=window_name,
                pane_title=pane_title,
                pane_current_command=pane_current_command,
            )
        )
    return workers


def sync_discovered_workers(
    state_db: Path,
    events_ndjson: Path,
    discovered_workers: list[DiscoveredWorker],
    *,
    observed_at: str | None = None,
    scope_socket: str | None = None,
    scope_session: str | None = None,
) -> list[dict[str, object]]:
    observed_at = observed_at or utc_now()
    event = EventRecord(
        event_id=f"evt-worker-discover-{uuid.uuid4().hex[:12]}",
        event_type="worker.discovery_refreshed",
        aggregate_type="worker_roster",
        aggregate_id="local-tmux",
        timestamp=observed_at,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-worker-discover-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload={
            "worker_ids": [worker.worker_id for worker in discovered_workers],
            "count": len(discovered_workers),
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        discovered_ids = [worker.worker_id for worker in discovered_workers]
        effective_scope_socket = scope_socket or (discovered_workers[0].tmux_socket if discovered_workers else None)
        effective_scope_session = scope_session or (discovered_workers[0].tmux_session if discovered_workers else None)

        for worker in discovered_workers:
            row = conn.execute(
                "SELECT state, operator_tags FROM workers WHERE worker_id = ?",
                (worker.worker_id,),
            ).fetchone()
            existing_tags = _load_json_list(row["operator_tags"]) if row else []
            merged_tags = sorted(set(existing_tags) | set(worker.operator_tags))
            next_state = worker.state
            if row is not None:
                if row["state"] == "quarantined":
                    next_state = "quarantined"
                elif MANUAL_DISABLE_TAG in existing_tags:
                    next_state = "unavailable"
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    runtime_type = excluded.runtime_type,
                    adapter_id = excluded.adapter_id,
                    tmux_socket = excluded.tmux_socket,
                    tmux_session = excluded.tmux_session,
                    tmux_pane = excluded.tmux_pane,
                    state = excluded.state,
                    capabilities = excluded.capabilities,
                    required_signal_status = excluded.required_signal_status,
                    last_evidence_at = excluded.last_evidence_at,
                    last_heartbeat_at = excluded.last_heartbeat_at,
                    interruptibility = excluded.interruptibility,
                    operator_tags = excluded.operator_tags
                """,
                (
                    worker.worker_id,
                    worker.runtime_type,
                    worker.adapter_id,
                    worker.tmux_socket,
                    worker.tmux_session,
                    worker.tmux_pane,
                    next_state,
                    json.dumps(worker.capabilities),
                    worker.required_signal_status,
                    worker.last_evidence_at,
                    worker.last_heartbeat_at,
                    worker.interruptibility,
                    json.dumps(merged_tags),
                ),
            )

        if effective_scope_socket and effective_scope_session:
            placeholders = ",".join("?" for _ in discovered_ids) if discovered_ids else "?"
            params: list[str] = [effective_scope_socket, effective_scope_session]
            if discovered_ids:
                sql = (
                    f"""
                    UPDATE workers
                    SET state = 'unavailable'
                    WHERE tmux_socket = ? AND tmux_session = ?
                      AND worker_id NOT IN ({placeholders})
                      AND state NOT IN ('quarantined', 'retired')
                    """
                )
                params.extend(discovered_ids)
            else:
                sql = """
                    UPDATE workers
                    SET state = 'unavailable'
                    WHERE tmux_socket = ? AND tmux_session = ?
                      AND state NOT IN ('quarantined', 'retired')
                """
            conn.execute(sql, tuple(params))

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return list_workers(state_db)


def list_workers(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                   state, capabilities, required_signal_status, last_evidence_at,
                   last_heartbeat_at, interruptibility, operator_tags
            FROM workers
            ORDER BY worker_id
            """
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_worker_dict(row) for row in rows]


def inspect_worker(state_db: Path, worker_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                   state, capabilities, required_signal_status, last_evidence_at,
                   last_heartbeat_at, interruptibility, operator_tags
            FROM workers
            WHERE worker_id = ?
            """,
            (worker_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise WorkerNotFoundError(f"Worker not found: {worker_id}")
    return _row_to_worker_dict(row)


def inspect_worker_context(state_db: Path, worker_id: str) -> dict[str, object]:
    worker = inspect_worker(state_db, worker_id)
    conn = connect_state_db(state_db)
    try:
        task_row = conn.execute(
            """
            SELECT task_id, title, state, current_lease_id
            FROM tasks
            WHERE current_worker_id = ?
            ORDER BY CASE WHEN state = 'active' THEN 0 ELSE 1 END, task_id
            LIMIT 1
            """,
            (worker_id,),
        ).fetchone()
        lease_row = None
        if task_row is not None and task_row["current_lease_id"]:
            lease_row = conn.execute(
                """
                SELECT lease_id, state, issued_at, accepted_at, ended_at, intervention_reason
                FROM leases
                WHERE lease_id = ?
                """,
                (task_row["current_lease_id"],),
            ).fetchone()
        metadata_row = conn.execute(
            "SELECT value FROM metadata WHERE key = 'assignments_blocked'"
        ).fetchone()
    finally:
        conn.close()

    assignments_blocked = bool(metadata_row and metadata_row["value"] == "1")
    next_action = None
    blocking_condition = None
    if task_row is not None and lease_row is not None:
        next_action = intervention_next_action(
            task_id=task_row["task_id"],
            task_state=task_row["state"],
            lease_state=lease_row["state"],
            owner_state=worker["state"],
            assignments_blocked=assignments_blocked,
        )
        blocking_condition = intervention_blocking_condition(
            task_state=task_row["state"],
            lease_state=lease_row["state"],
            owner_state=worker["state"],
            assignments_blocked=assignments_blocked,
        )

    worker["controller_truth"] = {
        "canonical_state": worker["state"],
        "routability": _build_routability(worker["state"]),
        "current_task": (
            {
                "task_id": task_row["task_id"],
                "summary": task_row["title"],
                "state": task_row["state"],
                "next_action": next_action,
                "blocking_condition": blocking_condition,
            }
            if task_row is not None
            else None
        ),
        "current_lease": (
            {
                "lease_id": lease_row["lease_id"],
                "state": lease_row["state"],
                "issued_at": lease_row["issued_at"],
                "accepted_at": lease_row["accepted_at"],
                "ended_at": lease_row["ended_at"],
                "intervention_reason": lease_row["intervention_reason"],
            }
            if lease_row is not None
            else None
        ),
        "pane_target": {
            "tmux_socket": worker["tmux_socket"],
            "tmux_session": worker["tmux_session"],
            "tmux_pane": worker["tmux_pane"],
        },
        "recent_event_refs": list_aggregate_events(state_db, worker_id),
    }
    worker["blocking_condition"] = blocking_condition
    worker["next_action"] = next_action
    return worker


def register_worker(
    state_db: Path,
    events_ndjson: Path,
    worker_id: str,
    adapter_id: str,
    *,
    target_state: str = "ready",
    event_type: str | None = None,
    event_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {"adapter_id": adapter_id, "state": target_state}
    if isinstance(event_payload, dict):
        payload.update(event_payload)
    return _update_worker(
        state_db,
        events_ndjson,
        worker_id,
        event_type=event_type or ("worker.quarantined" if target_state == "quarantined" else "worker.registered"),
        payload=payload,
        updater=lambda conn, row: conn.execute(
            """
            UPDATE workers
            SET adapter_id = ?, state = ?,
                operator_tags = ?
            WHERE worker_id = ?
            """,
            (
                adapter_id,
                "quarantined" if row["state"] == "quarantined" or target_state == "quarantined" else target_state,
                json.dumps(sorted(set(_load_json_list(row["operator_tags"])) | {"registered"})),
                worker_id,
            ),
        ),
    )


def set_worker_state(
    state_db: Path,
    events_ndjson: Path,
    worker_id: str,
    state: str,
) -> dict[str, object]:
    event_type_map = {
        "ready": "worker.enabled",
        "unavailable": "worker.disabled",
        "quarantined": "worker.quarantined",
    }
    if state not in event_type_map:
        raise RuntimeError(f"Unsupported worker state update: {state}")

    def updater(conn, row) -> None:
        tags = set(_load_json_list(row["operator_tags"]))
        if state == "unavailable":
            tags.add(MANUAL_DISABLE_TAG)
        else:
            tags.discard(MANUAL_DISABLE_TAG)
        conn.execute(
            "UPDATE workers SET state = ?, operator_tags = ? WHERE worker_id = ?",
            (state, json.dumps(sorted(tags)), worker_id),
        )

    return _update_worker(
        state_db,
        events_ndjson,
        worker_id,
        event_type=event_type_map[state],
        payload={"state": state},
        updater=updater,
    )


def resolve_tmux_context(
    repo_root: Path,
    *,
    tmux_socket: str | None = None,
    tmux_session: str | None = None,
) -> tuple[str, str]:
    paths = build_paths(repo_root)
    socket = tmux_socket or _resolve_socket(paths)
    session = tmux_session or _resolve_session(paths)
    if not socket:
        raise RuntimeError("Unable to resolve tmux socket for worker discovery")
    if not session:
        raise RuntimeError("Unable to resolve tmux session for worker discovery")
    return socket, session


def infer_runtime_type(window_name: str, pane_title: str, pane_current_command: str) -> str:
    haystack = " ".join(part.lower() for part in (window_name, pane_title, pane_current_command))
    if "claude" in haystack:
        return "claude"
    if "gemini" in haystack:
        return "gemini"
    if "codex" in haystack:
        return "codex"
    return "local"


def build_worker_id(runtime_type: str, session_name: str, pane_id: str) -> str:
    session_fragment = _slugify(session_name)
    pane_fragment = _slugify(pane_id)
    return f"worker-{runtime_type}-{session_fragment}-{pane_fragment}"


def _update_worker(state_db, events_ndjson, worker_id, *, event_type, payload, updater):
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-{event_type.replace('.', '-')}-{uuid.uuid4().hex[:12]}",
        event_type=event_type,
        aggregate_type="worker",
        aggregate_id=worker_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-{event_type.replace('.', '-')}-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload=payload,
        redaction_level="none",
    )

    def mutator(conn) -> None:
        row = conn.execute("SELECT worker_id, operator_tags, state FROM workers WHERE worker_id = ?", (worker_id,)).fetchone()
        if row is None:
            raise WorkerNotFoundError(f"Worker not found: {worker_id}")
        updater(conn, row)

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return inspect_worker(state_db, worker_id)


def _resolve_socket(paths) -> str:
    env_socket = os.environ.get("TMUX_SOCKET")
    if env_socket and _socket_is_live(env_socket):
        return env_socket
    if paths.repo_root.joinpath(".codex", "tmux-socket.txt").exists():
        candidate = paths.repo_root.joinpath(".codex", "tmux-socket.txt").read_text(encoding="utf-8").strip()
        if candidate and _socket_is_live(candidate):
            return candidate
    return env_socket or ""


def _resolve_session(paths) -> str:
    session_file = paths.repo_root / ".codex" / "tmux-session.txt"
    if session_file.exists():
        return session_file.read_text(encoding="utf-8").strip()
    return os.environ.get("TMUX_SESSION", "")


def _socket_is_live(socket_path: str) -> bool:
    if not socket_path:
        return False
    result = subprocess.run(
        ["tmux", "-S", socket_path, "list-sessions"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _tmux(socket_path: str, args: list[str]) -> str:
    result = subprocess.run(
        ["tmux", "-S", socket_path, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "tmux command failed")
    return result.stdout


def _row_to_worker_dict(row) -> dict[str, object]:
    freshness_seconds = _freshness_seconds(row["last_evidence_at"])
    return {
        "worker_id": row["worker_id"],
        "runtime_type": row["runtime_type"],
        "runtime": row["runtime_type"],
        "adapter_id": row["adapter_id"],
        "tmux_socket": row["tmux_socket"],
        "tmux_session": row["tmux_session"],
        "tmux_pane": row["tmux_pane"],
        "state": row["state"],
        "capabilities": _load_json_list(row["capabilities"]),
        "required_signal_status": row["required_signal_status"],
        "last_evidence_at": row["last_evidence_at"],
        "last_heartbeat_at": row["last_heartbeat_at"],
        "freshness_seconds": freshness_seconds,
        "interruptibility": row["interruptibility"],
        "operator_tags": _load_json_list(row["operator_tags"]),
    }


def _load_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    loaded = json.loads(value)
    return loaded if isinstance(loaded, list) else []


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _freshness_seconds(value: str | None) -> int:
    if not value:
        return 0
    try:
        observed_at = datetime.fromisoformat(value)
    except ValueError:
        return 0
    return max(0, int((datetime.now(timezone.utc) - observed_at).total_seconds()))


def _build_routability(state: str) -> dict[str, object]:
    if state in {"degraded", "unavailable", "quarantined"}:
        return {
            "assignable": False,
            "reason": f"worker_state_{state}",
        }
    return {
        "assignable": True,
        "reason": "assignable",
    }
