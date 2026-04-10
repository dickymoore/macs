#!/usr/bin/env python3
"""Protected surface lock helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class LockConflictError(RuntimeError):
    """Raised when protected surfaces conflict with existing held locks."""


def normalize_surface(surface_ref: str) -> tuple[str, str]:
    if surface_ref.startswith("logical:"):
        return ("logical", surface_ref.removeprefix("logical:"))
    if surface_ref.endswith("/"):
        return ("directory", surface_ref.rstrip("/"))
    return ("file", surface_ref)


def check_lock_conflicts(state_db: Path, protected_surfaces: list[str]) -> dict[str, object]:
    requested = [normalize_surface(surface) for surface in protected_surfaces]
    conn = connect_state_db(state_db)
    try:
        active_locks = conn.execute(
            """
            SELECT lock_id, target_type, target_ref, task_id, lease_id, state
            FROM locks
            WHERE state IN ('reserved', 'active')
            ORDER BY lock_id
            """
        ).fetchall()
    finally:
        conn.close()

    conflicts = []
    for target_type, target_ref in requested:
        for row in active_locks:
            if surfaces_conflict((target_type, target_ref), (row["target_type"], row["target_ref"])):
                conflicts.append(
                    {
                        "surface_ref": surface_ref_for(target_type, target_ref),
                        "conflicting_lock_id": row["lock_id"],
                        "conflicting_surface_ref": surface_ref_for(row["target_type"], row["target_ref"]),
                        "task_id": row["task_id"],
                        "lease_id": row["lease_id"],
                    }
                )
    return {"ok": not conflicts, "conflicts": conflicts}


def reserve_locks_for_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    lease_id: str,
    protected_surfaces: list[str],
    policy_origin: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_metadata: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    conflict_result = check_lock_conflicts(state_db, protected_surfaces)
    if not conflict_result["ok"]:
        raise LockConflictError(json.dumps(conflict_result["conflicts"], sort_keys=True))

    reserved_locks = []
    created_at = utc_now()
    event = EventRecord(
        event_id=f"evt-lock-reserve-{uuid.uuid4().hex[:12]}",
        event_type="lock.reserved",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=created_at,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id or f"corr-lock-reserve-{uuid.uuid4().hex[:12]}",
        causation_id=causation_id,
        payload={
            "task_id": task_id,
            "protected_surfaces": protected_surfaces,
            **(event_metadata or {}),
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        for surface in protected_surfaces:
            target_type, target_ref = normalize_surface(surface)
            lock_id = f"lock-{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lock_id,
                    target_type,
                    target_ref,
                    "exclusive_write",
                    "reserved",
                    task_id,
                    lease_id,
                    policy_origin,
                    created_at,
                    None,
                ),
            )
            reserved_locks.append(
                {
                    "lock_id": lock_id,
                    "surface_ref": surface_ref_for(target_type, target_ref),
                    "task_id": task_id,
                    "lease_id": lease_id,
                    "state": "reserved",
                }
            )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return reserved_locks


def release_locks_for_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    lease_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_metadata: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    released_locks: list[dict[str, object]] = []
    released_at = utc_now()
    event = EventRecord(
        event_id=f"evt-lock-release-{uuid.uuid4().hex[:12]}",
        event_type="lock.released",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=released_at,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id or f"corr-lock-release-{uuid.uuid4().hex[:12]}",
        causation_id=causation_id,
        payload={
            "task_id": task_id,
            "lease_id": lease_id,
            **(event_metadata or {}),
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        query = """
            SELECT lock_id, target_type, target_ref, task_id, lease_id
            FROM locks
            WHERE task_id = ? AND state IN ('reserved', 'active')
        """
        params: tuple[object, ...] = (task_id,)
        if lease_id is not None:
            query += " AND lease_id = ?"
            params = (task_id, lease_id)
        rows = conn.execute(query, params).fetchall()
        for row in rows:
            conn.execute(
                """
                UPDATE locks
                SET state = 'released', released_at = ?
                WHERE lock_id = ?
                """,
                (released_at, row["lock_id"]),
            )
            released_locks.append(
                {
                    "lock_id": row["lock_id"],
                    "surface_ref": surface_ref_for(row["target_type"], row["target_ref"]),
                    "task_id": row["task_id"],
                    "lease_id": row["lease_id"],
                    "state": "released",
                    "released_at": released_at,
                }
            )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return released_locks


def activate_locks_for_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    lease_id: str,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    event_metadata: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    active_locks: list[dict[str, object]] = []
    activated_at = utc_now()
    event = EventRecord(
        event_id=f"evt-lock-activate-{uuid.uuid4().hex[:12]}",
        event_type="lock.activated",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=activated_at,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id or f"corr-lock-activate-{uuid.uuid4().hex[:12]}",
        causation_id=causation_id,
        payload={
            "task_id": task_id,
            "lease_id": lease_id,
            **(event_metadata or {}),
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        rows = conn.execute(
            """
            SELECT lock_id, target_type, target_ref, task_id, lease_id
            FROM locks
            WHERE task_id = ? AND lease_id = ? AND state = 'reserved'
            """,
            (task_id, lease_id),
        ).fetchall()
        for row in rows:
            conn.execute(
                "UPDATE locks SET state = 'active' WHERE lock_id = ?",
                (row["lock_id"],),
            )
            active_locks.append(
                {
                    "lock_id": row["lock_id"],
                    "surface_ref": surface_ref_for(row["target_type"], row["target_ref"]),
                    "task_id": row["task_id"],
                    "lease_id": row["lease_id"],
                    "state": "active",
                }
            )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return active_locks


def list_locks(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
            FROM locks
            ORDER BY created_at, lock_id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "lock_id": row["lock_id"],
            "surface_ref": surface_ref_for(row["target_type"], row["target_ref"]),
            "mode": row["mode"],
            "state": row["state"],
            "task_id": row["task_id"],
            "lease_id": row["lease_id"],
            "policy_origin": row["policy_origin"],
            "created_at": row["created_at"],
            "released_at": row["released_at"],
        }
        for row in rows
    ]


def inspect_lock(state_db: Path, lock_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
            FROM locks
            WHERE lock_id = ?
            """,
            (lock_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise RuntimeError(f"Lock not found: {lock_id}")
    return {
        "lock_id": row["lock_id"],
        "surface_ref": surface_ref_for(row["target_type"], row["target_ref"]),
        "mode": row["mode"],
        "state": row["state"],
        "task_id": row["task_id"],
        "lease_id": row["lease_id"],
        "policy_origin": row["policy_origin"],
        "created_at": row["created_at"],
        "released_at": row["released_at"],
    }


def surfaces_conflict(left: tuple[str, str], right: tuple[str, str]) -> bool:
    left_type, left_ref = left
    right_type, right_ref = right
    if left_type == "logical" or right_type == "logical":
        return left_ref == right_ref
    if left_ref == right_ref:
        return True
    if left_type == "directory" and right_ref.startswith(left_ref.rstrip("/") + "/"):
        return True
    if right_type == "directory" and left_ref.startswith(right_ref.rstrip("/") + "/"):
        return True
    return False


def surface_ref_for(target_type: str, target_ref: str) -> str:
    if target_type == "logical":
        return f"logical:{target_ref}"
    if target_type == "directory":
        return f"{target_ref}/"
    return target_ref
