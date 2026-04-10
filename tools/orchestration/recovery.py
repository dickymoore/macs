#!/usr/bin/env python3
"""Startup recovery and restart-safe reconciliation helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.history import decision_event_for_ref, inspect_lease, latest_intervention_decision, list_aggregate_events
from tools.orchestration.interventions import intervention_blocking_condition, intervention_next_action
from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction

TERMINAL_RECOVERY_RUN_STATES = {"completed", "abandoned"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class StartupRecoverySummary:
    restored_workers: int
    restored_tasks: int
    restored_leases: int
    restored_locks: int
    restored_events: int
    tasks_pending_reconciliation: list[str]
    live_leases_pending_reconciliation: list[str]
    suspended_lease_ids: list[str]
    unreleased_lock_count: int
    assignments_blocked: bool
    recovery_run_id: str | None
    pending_recovery_runs: list[dict[str, object]]

    def as_dict(self) -> dict[str, object]:
        return {
            "restored_entities": {
                "workers": self.restored_workers,
                "tasks": self.restored_tasks,
                "leases": self.restored_leases,
                "locks": self.restored_locks,
                "events": self.restored_events,
            },
            "unresolved_anomalies": {
                "tasks_pending_reconciliation": self.tasks_pending_reconciliation,
                "live_leases_pending_reconciliation": self.live_leases_pending_reconciliation,
                "suspended_lease_ids": self.suspended_lease_ids,
                "unreleased_lock_count": self.unreleased_lock_count,
            },
            "assignments_blocked": self.assignments_blocked,
            "recovery_run_id": self.recovery_run_id,
            "pending_recovery_runs": self.pending_recovery_runs,
        }


def restore_startup_state(
    state_db: Path,
    events_ndjson: Path,
    *,
    timestamp: str | None = None,
    actor_id: str = "controller-main",
) -> StartupRecoverySummary:
    scan = _scan_startup_state(state_db)
    pending_recovery_runs = [
        {
            "recovery_run_id": row["recovery_run_id"],
            "task_id": row["task_id"],
            "state": row["state"],
            "recommended_action": row["decision_summary"].get("recommended_action"),
        }
        for row in list_unresolved_recovery_runs(state_db)
    ]
    timestamp = timestamp or utc_now()
    recovery_run_id = f"recovery-startup-{uuid.uuid4().hex[:12]}" if scan["assignments_blocked"] else None
    if recovery_run_id is not None and not any(
        item["recovery_run_id"] == recovery_run_id for item in pending_recovery_runs
    ):
        pending_recovery_runs.append(
            {
                "recovery_run_id": recovery_run_id,
                "task_id": None,
                "state": "pending_reconciliation",
                "recommended_action": "startup_reconciliation_required",
            }
        )

    payload = {
        "restored_entities": scan["restored_entities"],
        "unresolved_anomalies": {
            "tasks_pending_reconciliation": scan["task_ids"],
            "live_leases_pending_reconciliation": scan["live_lease_ids"],
            "suspended_lease_ids": scan["lease_ids_to_suspend"],
            "unreleased_lock_count": scan["unreleased_lock_count"],
        },
        "assignments_blocked": scan["assignments_blocked"],
        "recovery_run_id": recovery_run_id,
        "pending_recovery_runs": pending_recovery_runs,
    }
    event = EventRecord(
        event_id=f"evt-startup-recovery-{uuid.uuid4().hex[:12]}",
        event_type="controller.startup_recovery_completed",
        aggregate_type="controller",
        aggregate_id="controller-main",
        timestamp=timestamp,
        actor_type="controller",
        actor_id=actor_id,
        correlation_id=recovery_run_id or f"startup-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload=payload,
        redaction_level="none",
    )

    def mutator(conn) -> None:
        for lease_id in scan["lease_ids_to_suspend"]:
            conn.execute("UPDATE leases SET state = 'suspended' WHERE lease_id = ?", (lease_id,))
        for task_id in scan["task_ids"]:
            conn.execute("UPDATE tasks SET state = 'reconciliation' WHERE task_id = ?", (task_id,))

        _set_metadata(conn, "assignments_blocked", "1" if scan["assignments_blocked"] else "0")
        _set_metadata(conn, "startup_summary", json.dumps(payload, sort_keys=True))
        _set_metadata(conn, "last_startup_at", timestamp)
        if recovery_run_id is not None:
            conn.execute(
                """
                INSERT INTO recovery_runs (
                    recovery_run_id, task_id, state, started_at, ended_at,
                    anomaly_summary, decision_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recovery_run_id,
                    None,
                    "pending_reconciliation",
                    timestamp,
                    None,
                    json.dumps(payload["unresolved_anomalies"], sort_keys=True),
                    json.dumps(
                        {
                            "action": "startup_reconciliation_required",
                            "assignments_blocked": True,
                        },
                        sort_keys=True,
                    ),
                ),
            )
            _set_metadata(conn, "last_recovery_run_id", recovery_run_id)

    write_eventful_transaction(state_db, events_ndjson, event, mutator)

    restored = scan["restored_entities"]
    return StartupRecoverySummary(
        restored_workers=restored["workers"],
        restored_tasks=restored["tasks"],
        restored_leases=restored["leases"],
        restored_locks=restored["locks"],
        restored_events=restored["events"],
        tasks_pending_reconciliation=scan["task_ids"],
        live_leases_pending_reconciliation=scan["live_lease_ids"],
        suspended_lease_ids=scan["lease_ids_to_suspend"],
        unreleased_lock_count=scan["unreleased_lock_count"],
        assignments_blocked=scan["assignments_blocked"],
        recovery_run_id=recovery_run_id,
        pending_recovery_runs=pending_recovery_runs,
    )


def _scan_startup_state(state_db: Path) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        restored_entities = {
            "workers": conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0],
            "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            "leases": conn.execute("SELECT COUNT(*) FROM leases").fetchone()[0],
            "locks": conn.execute("SELECT COUNT(*) FROM locks").fetchone()[0],
            "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        }
        live_rows = conn.execute(
            """
            SELECT leases.lease_id, leases.state AS lease_state, tasks.task_id
            FROM leases
            INNER JOIN tasks ON tasks.task_id = leases.task_id
            WHERE leases.state IN ('pending_accept', 'active', 'paused', 'suspended', 'expiring')
            ORDER BY tasks.task_id, leases.lease_id
            """
        ).fetchall()
        task_ids = sorted({row["task_id"] for row in live_rows})
        live_lease_ids = [row["lease_id"] for row in live_rows]
        lease_ids_to_suspend = [
            row["lease_id"] for row in live_rows if row["lease_state"] in {"active", "paused"}
        ]
        unreleased_lock_count = conn.execute(
            "SELECT COUNT(*) FROM locks WHERE released_at IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "restored_entities": restored_entities,
        "task_ids": task_ids,
        "live_lease_ids": live_lease_ids,
        "lease_ids_to_suspend": lease_ids_to_suspend,
        "unreleased_lock_count": unreleased_lock_count,
        "assignments_blocked": bool(task_ids),
    }


def inspect_recovery_context(state_db: Path, *, task_id: str) -> dict[str, object]:
    task = _inspect_task_row(state_db, task_id)
    recovery_run = get_latest_recovery_run(state_db, task_id=task_id)
    if recovery_run is None and task["state"] in {"intervention_hold", "reconciliation"}:
        recovery_run = ensure_recovery_run(state_db, task_id=task_id)
    anomaly_summary = recovery_run.get("anomaly_summary", {}) if recovery_run is not None else {}
    decision_summary = recovery_run.get("decision_summary", {}) if recovery_run is not None else {}
    current_lease = inspect_lease(state_db, task["current_lease_id"]) if task["current_lease_id"] else None
    current_worker = _maybe_worker_row(state_db, task["current_worker_id"]) if task["current_worker_id"] else None
    assignments_blocked = _metadata_value(state_db, "assignments_blocked") == "1"
    blocking_condition = intervention_blocking_condition(
        task_state=task["state"],
        lease_state=current_lease["state"] if current_lease is not None else None,
        owner_state=current_worker["state"] if current_worker is not None else None,
        assignments_blocked=assignments_blocked,
    )
    next_action = intervention_next_action(
        task_id=task["task_id"],
        task_state=task["state"],
        lease_state=current_lease["state"] if current_lease is not None else None,
        owner_state=current_worker["state"] if current_worker is not None else None,
        assignments_blocked=assignments_blocked,
    )
    if (
        recovery_run is not None
        and recovery_run["ended_at"] is None
        and recovery_run["state"] not in TERMINAL_RECOVERY_RUN_STATES
        and task["state"] == "reconciliation"
        and (current_lease is None or recovery_run["state"] == "pending_retry")
    ):
        blocking_condition = "interrupted recovery run is blocking successor routing"
        if decision_summary.get("recommended_action") == "retry":
            next_action = f"macs recovery retry --task {task_id}"
        elif decision_summary.get("allowed_next_actions"):
            next_action = str(decision_summary["allowed_next_actions"][0])

    recent_event_refs = (
        list_aggregate_events(state_db, str(recovery_run["recovery_run_id"]))
        if recovery_run is not None
        else []
    )
    latest_decision = decision_event_for_ref(state_db, recent_event_refs[0] if recent_event_refs else None)
    if latest_decision is None:
        latest_decision = latest_intervention_decision(state_db, task_id)

    return {
        "recovery_run": (
            {
                "recovery_run_id": recovery_run["recovery_run_id"],
                "state": recovery_run["state"],
                "started_at": recovery_run["started_at"],
                "ended_at": recovery_run["ended_at"],
            }
            if recovery_run is not None
            else None
        ),
        "anomaly_summary": anomaly_summary,
        "frozen_objects": {
            "task_id": task["task_id"],
            "lease_id": task["current_lease_id"],
            "worker_id": task["current_worker_id"],
        },
        "current_state": {
            "task_id": task["task_id"],
            "task_state": task["state"],
            "current_worker_id": task["current_worker_id"],
            "current_worker_state": current_worker["state"] if current_worker is not None else None,
            "current_lease_id": task["current_lease_id"],
            "current_lease_state": current_lease["state"] if current_lease is not None else None,
            "intervention_reason": current_lease["intervention_reason"] if current_lease is not None else None,
        },
        "proposed_state": {
            "selected_worker_id": decision_summary.get("proposed_worker_id"),
            "workflow_class": decision_summary.get("proposed_workflow_class"),
            "recommended_action": decision_summary.get("recommended_action"),
        },
        "latest_intervention_decision": latest_decision,
        "recent_event_refs": recent_event_refs,
        "allowed_next_actions": decision_summary.get("allowed_next_actions", []),
        "blocking_condition": blocking_condition,
        "next_action": next_action,
    }


def ensure_recovery_run(
    state_db: Path,
    *,
    task_id: str,
    state: str = "pending_operator_action",
    proposed_worker_id: str | None = None,
    proposed_workflow_class: str | None = None,
) -> dict[str, object]:
    task = _inspect_task_row(state_db, task_id)
    current_lease = inspect_lease(state_db, task["current_lease_id"]) if task["current_lease_id"] else None
    current_worker = _maybe_worker_row(state_db, task["current_worker_id"]) if task["current_worker_id"] else None
    anomaly_summary = {
        "kind": "ambiguous_ownership" if task["state"] == "reconciliation" else "recovery_required",
        "basis": current_lease["intervention_reason"] if current_lease is not None else None,
        "predecessor_worker_id": task["current_worker_id"],
        "predecessor_lease_id": task["current_lease_id"],
    }
    recommended_action = "reroute" if proposed_worker_id or proposed_workflow_class else "inspect"
    allowed_next_actions = [f"macs task inspect --task {task_id}"]
    if proposed_worker_id:
        allowed_next_actions.insert(0, f"macs task reroute --task {task_id} --worker {proposed_worker_id}")
    elif proposed_workflow_class or task.get("workflow_class"):
        allowed_next_actions.insert(
            0,
            f"macs task reroute --task {task_id} --workflow-class {proposed_workflow_class or task['workflow_class']}",
        )
    decision_summary = {
        "allowed_next_actions": allowed_next_actions,
        "proposed_worker_id": proposed_worker_id,
        "proposed_workflow_class": proposed_workflow_class or task.get("workflow_class"),
        "recommended_action": recommended_action,
        "current_worker_state": current_worker["state"] if current_worker is not None else None,
        "current_lease_state": current_lease["state"] if current_lease is not None else None,
    }
    return _upsert_recovery_run(
        state_db,
        task_id=task_id,
        state=state,
        anomaly_summary=anomaly_summary,
        decision_summary=decision_summary,
        ended_at=None,
    )


def complete_recovery_run(
    state_db: Path,
    *,
    task_id: str,
    replacement_lease_id: str,
    selected_worker_id: str,
) -> dict[str, object]:
    latest = ensure_recovery_run(state_db, task_id=task_id)
    decision_summary = dict(latest["decision_summary"])
    decision_summary["selected_worker_id"] = selected_worker_id
    decision_summary["replacement_lease_id"] = replacement_lease_id
    decision_summary["recommended_action"] = "completed"
    return _upsert_recovery_run(
        state_db,
        task_id=task_id,
        state="completed",
        anomaly_summary=latest["anomaly_summary"],
        decision_summary=decision_summary,
        ended_at=utc_now(),
    )


def abandon_recovery_run(
    state_db: Path,
    *,
    task_id: str,
) -> dict[str, object]:
    latest = get_unresolved_recovery_run(state_db, task_id=task_id)
    if latest is None:
        raise RuntimeError(f"Task {task_id} has no unresolved recovery run")
    decision_summary = dict(latest["decision_summary"])
    decision_summary["recommended_action"] = "fresh_action_required"
    allowed_next_actions = [f"macs task inspect --task {task_id}"]
    if decision_summary.get("proposed_worker_id"):
        allowed_next_actions.insert(0, f"macs task assign --task {task_id} --worker {decision_summary['proposed_worker_id']}")
    elif decision_summary.get("proposed_workflow_class"):
        allowed_next_actions.insert(
            0,
            f"macs task assign --task {task_id} --workflow-class {decision_summary['proposed_workflow_class']}",
        )
    decision_summary["allowed_next_actions"] = allowed_next_actions
    return _upsert_recovery_run(
        state_db,
        task_id=task_id,
        state="abandoned",
        anomaly_summary=latest["anomaly_summary"],
        decision_summary=decision_summary,
        ended_at=utc_now(),
    )


def get_unresolved_recovery_run(state_db: Path, *, task_id: str) -> dict[str, object] | None:
    latest = get_latest_recovery_run(state_db, task_id=task_id)
    if latest is None:
        return None
    if latest["ended_at"] is not None or latest["state"] in TERMINAL_RECOVERY_RUN_STATES:
        return None
    return latest


def list_unresolved_recovery_runs(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT recovery_run_id, task_id, state, started_at, ended_at, anomaly_summary, decision_summary
            FROM recovery_runs
            WHERE ended_at IS NULL AND state NOT IN ('completed', 'abandoned')
            ORDER BY started_at, recovery_run_id
            """
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        item = dict(row)
        item["anomaly_summary"] = json.loads(item["anomaly_summary"] or "{}")
        item["decision_summary"] = json.loads(item["decision_summary"] or "{}")
        items.append(item)
    return items


def get_latest_recovery_run(state_db: Path, *, task_id: str) -> dict[str, object] | None:
    return _latest_recovery_run(state_db, task_id=task_id)


def _set_metadata(conn, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO metadata(key, value) VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def _metadata_value(state_db: Path, key: str) -> str | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row["value"]


def _inspect_task_row(state_db: Path, task_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT task_id, state, current_worker_id, current_lease_id, workflow_class
            FROM tasks
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError(f"Task not found: {task_id}")
    return dict(row)


def _latest_recovery_run(state_db: Path, *, task_id: str) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT recovery_run_id, task_id, state, started_at, ended_at, anomaly_summary, decision_summary
            FROM recovery_runs
            WHERE task_id = ?
            ORDER BY started_at DESC, recovery_run_id DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    item = dict(row)
    item["anomaly_summary"] = json.loads(item["anomaly_summary"] or "{}")
    item["decision_summary"] = json.loads(item["decision_summary"] or "{}")
    return item


def _upsert_recovery_run(
    state_db: Path,
    *,
    task_id: str,
    state: str,
    anomaly_summary: dict[str, object],
    decision_summary: dict[str, object],
    ended_at: str | None,
) -> dict[str, object]:
    latest = get_latest_recovery_run(state_db, task_id=task_id)
    conn = connect_state_db(state_db)
    try:
        if latest is None or latest["ended_at"] is not None:
            recovery_run_id = f"recovery-task-{uuid.uuid4().hex[:12]}"
            started_at = utc_now()
            conn.execute(
                """
                INSERT INTO recovery_runs (
                    recovery_run_id, task_id, state, started_at, ended_at, anomaly_summary, decision_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recovery_run_id,
                    task_id,
                    state,
                    started_at,
                    ended_at,
                    json.dumps(anomaly_summary, sort_keys=True),
                    json.dumps(decision_summary, sort_keys=True),
                ),
            )
        else:
            recovery_run_id = latest["recovery_run_id"]
            conn.execute(
                """
                UPDATE recovery_runs
                SET state = ?, ended_at = ?, anomaly_summary = ?, decision_summary = ?
                WHERE recovery_run_id = ?
                """,
                (
                    state,
                    ended_at,
                    json.dumps(anomaly_summary, sort_keys=True),
                    json.dumps(decision_summary, sort_keys=True),
                    recovery_run_id,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    row = get_latest_recovery_run(state_db, task_id=task_id)
    if row is None:
        raise RuntimeError(f"Recovery run not found after update for task {task_id}")
    return row


def _inspect_worker_row(state_db: Path, worker_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT worker_id, state
            FROM workers
            WHERE worker_id = ?
            """,
            (worker_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError(f"Worker not found: {worker_id}")
    return dict(row)


def _maybe_worker_row(state_db: Path, worker_id: str) -> dict[str, object] | None:
    try:
        return _inspect_worker_row(state_db, worker_id)
    except RuntimeError:
        return None
