#!/usr/bin/env python3
"""Controller overview summary helpers."""

from __future__ import annotations

from pathlib import Path

from tools.orchestration.history import list_events
from tools.orchestration.locks import list_locks
from tools.orchestration.tasks import list_tasks
from tools.orchestration.workers import list_workers


def build_overview(state_db: Path) -> dict[str, object]:
    workers = list_workers(state_db)
    tasks = list_tasks(state_db)
    locks = list_locks(state_db)
    events = list_events(state_db)

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

    return {
        "active_alerts": active_alerts,
        "worker_summary": worker_counts,
        "task_summary": task_counts,
        "active_tasks": [
            {
                "task_id": task["task_id"],
                "state": task["state"],
                "current_worker_id": task["current_worker_id"],
                "current_lease_id": task["current_lease_id"],
            }
            for task in tasks
            if task["state"] in {"reserved", "active", "intervention_hold", "reconciliation"}
        ],
        "locks": {
            "held_or_reserved": len([lock for lock in locks if lock["state"] in {"reserved", "active"}]),
            "conflicted": len([lock for lock in locks if lock["state"] == "conflicted"]),
        },
        "recent_events": events[-5:],
    }
