#!/usr/bin/env python3
"""Controller overview summary helpers."""

from __future__ import annotations

from pathlib import Path

from tools.orchestration.history import inspect_lease, list_events
from tools.orchestration.interventions import intervention_blocking_condition, intervention_next_action
from tools.orchestration.locks import list_locks
from tools.orchestration.recovery import inspect_recovery_context
from tools.orchestration.tasks import list_tasks
from tools.orchestration.workers import list_workers


def build_overview(state_db: Path) -> dict[str, object]:
    workers = list_workers(state_db)
    tasks = list_tasks(state_db)
    locks = list_locks(state_db)
    events = list_events(state_db)
    worker_states = {worker["worker_id"]: worker["state"] for worker in workers}
    assignments_blocked = _metadata_value(state_db, "assignments_blocked") == "1"

    worker_counts = {}
    for worker in workers:
        worker_counts[worker["state"]] = worker_counts.get(worker["state"], 0) + 1

    task_counts = {}
    for task in tasks:
        task_counts[task["state"]] = task_counts.get(task["state"], 0) + 1

    active_alerts = []
    for worker in workers:
        if worker["state"] in {"degraded", "unavailable", "quarantined"}:
            active_alerts.append(
                {
                    "kind": "worker_state",
                    "worker_id": worker["worker_id"],
                    "state": worker["state"],
                }
            )

    active_tasks = []
    for task in tasks:
        if task["state"] not in {"reserved", "active", "intervention_hold", "reconciliation"}:
            continue
        lease = inspect_lease(state_db, task["current_lease_id"]) if task["current_lease_id"] else None
        owner_state = worker_states.get(task["current_worker_id"])
        next_action = intervention_next_action(
            task_id=task["task_id"],
            task_state=task["state"],
            lease_state=lease["state"] if lease is not None else None,
            owner_state=owner_state,
            assignments_blocked=assignments_blocked,
        )
        blocking_condition = intervention_blocking_condition(
            task_state=task["state"],
            lease_state=lease["state"] if lease is not None else None,
            owner_state=owner_state,
            assignments_blocked=assignments_blocked,
        )
        recovery = inspect_recovery_context(state_db, task_id=task["task_id"])
        if recovery.get("blocking_condition") is not None:
            blocking_condition = recovery["blocking_condition"]
        if recovery.get("next_action") is not None:
            next_action = recovery["next_action"]
        item = {
            "task_id": task["task_id"],
            "state": task["state"],
            "current_worker_id": task["current_worker_id"],
            "current_lease_id": task["current_lease_id"],
            "lease_state": lease["state"] if lease is not None else None,
            "intervention_reason": lease["intervention_reason"] if lease is not None else None,
            "next_action": next_action,
            "blocking_condition": blocking_condition,
        }
        if recovery.get("recovery_run") is not None:
            item["recovery_run_id"] = recovery["recovery_run"]["recovery_run_id"]
            item["recovery_run_state"] = recovery["recovery_run"]["state"]
        active_tasks.append(item)
        if task["state"] == "intervention_hold" and lease is not None:
            alert = {
                "kind": "task_hold",
                "task_id": task["task_id"],
                "state": task["state"],
                "lease_state": lease["state"],
                "intervention_reason": lease["intervention_reason"],
                "blocking_condition": blocking_condition,
                "next_action": next_action,
            }
            if recovery.get("recovery_run") is not None:
                alert["recovery_run_id"] = recovery["recovery_run"]["recovery_run_id"]
                alert["recovery_run_state"] = recovery["recovery_run"]["state"]
            active_alerts.append(alert)

    return {
        "active_alerts": active_alerts,
        "worker_summary": worker_counts,
        "task_summary": task_counts,
        "active_tasks": active_tasks,
        "locks": {
            "held_or_reserved": len([lock for lock in locks if lock["state"] in {"reserved", "active", "held"}]),
            "conflicted": len([lock for lock in locks if lock["state"] == "conflicted"]),
        },
        "recent_events": events[-5:],
    }


def _metadata_value(state_db: Path, key: str) -> str | None:
    from tools.orchestration.store import connect_state_db

    conn = connect_state_db(state_db)
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row["value"]
