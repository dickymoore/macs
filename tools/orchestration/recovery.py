#!/usr/bin/env python3
"""Startup recovery and restart-safe reconciliation helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction


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
        }


def restore_startup_state(
    state_db: Path,
    events_ndjson: Path,
    *,
    timestamp: str | None = None,
    actor_id: str = "controller-main",
) -> StartupRecoverySummary:
    scan = _scan_startup_state(state_db)
    timestamp = timestamp or utc_now()
    recovery_run_id = f"recovery-startup-{uuid.uuid4().hex[:12]}" if scan["assignments_blocked"] else None

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
            WHERE leases.state IN ('active', 'paused', 'suspended', 'expiring')
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


def _set_metadata(conn, key: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO metadata(key, value) VALUES(?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
