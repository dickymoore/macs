#!/usr/bin/env python3
"""Task creation, inspection, and assignment helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.invariants import InvariantViolationError
from tools.orchestration.locks import LockConflictError, check_lock_conflicts, reserve_locks_for_task
from tools.orchestration.routing import RoutingError, evaluate_task_routing, inspect_routing_decision, persist_routing_decision
from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class TaskNotFoundError(RuntimeError):
    """Raised when a requested task does not exist."""


def create_task_record(
    state_db: Path,
    events_ndjson: Path,
    *,
    summary: str,
    workflow_class: str,
    required_capabilities: list[str],
    protected_surfaces: list[str],
    priority: str = "normal",
) -> dict[str, object]:
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-task-create-{uuid.uuid4().hex[:12]}",
        event_type="task.created",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-task-create-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload={
            "summary": summary,
            "workflow_class": workflow_class,
            "required_capabilities": required_capabilities,
            "protected_surfaces": protected_surfaces,
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        conn.execute(
            """
            INSERT INTO tasks (
                task_id, title, description, workflow_class, intent,
                required_capabilities, protected_surfaces, priority, state,
                current_worker_id, current_lease_id, routing_policy_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                summary,
                summary,
                workflow_class,
                summary,
                json.dumps(required_capabilities),
                json.dumps(protected_surfaces),
                priority,
                "pending_assignment",
                None,
                None,
                None,
            ),
        )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return inspect_task(state_db, task_id)


def list_tasks(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT task_id, title, workflow_class, required_capabilities, protected_surfaces,
                   priority, state, current_worker_id, current_lease_id, routing_policy_ref
            FROM tasks
            ORDER BY task_id
            """
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_task(row) for row in rows]


def inspect_task(state_db: Path, task_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT task_id, title, workflow_class, required_capabilities, protected_surfaces,
                   priority, state, current_worker_id, current_lease_id, routing_policy_ref
            FROM tasks
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise TaskNotFoundError(f"Task not found: {task_id}")
    task = _row_to_task(row)
    task["routing_decision"] = inspect_routing_decision(state_db, task_id)
    return task


def assign_task(
    repo_root: Path,
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    explicit_worker_id: str | None = None,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    evaluation = evaluate_task_routing(repo_root, state_db, task, explicit_worker_id=explicit_worker_id)
    if evaluation.selected_worker_id is None:
        raise RoutingError("No eligible workers for task")
    lock_check = check_lock_conflicts(state_db, task["protected_surfaces"])
    if not lock_check["ok"]:
        raise LockConflictError(json.dumps(lock_check["conflicts"], sort_keys=True))

    decision = persist_routing_decision(state_db, events_ndjson, task_id, evaluation, lock_check_result=lock_check)
    lease_id = f"lease-{uuid.uuid4().hex[:12]}"
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-task-assign-{uuid.uuid4().hex[:12]}",
        event_type="task.assigned",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-task-assign-{uuid.uuid4().hex[:12]}",
        causation_id=decision["decision_id"],
        payload={
            "task_id": task_id,
            "worker_id": evaluation.selected_worker_id,
            "lease_id": lease_id,
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        current = conn.execute(
            "SELECT state, current_worker_id, current_lease_id FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if current is None:
            raise TaskNotFoundError(f"Task not found: {task_id}")
        if current["state"] not in {"pending_assignment", "reconciliation"}:
            raise InvariantViolationError(f"Task {task_id} is not assignable from state {current['state']}")
        if current["current_lease_id"] is not None:
            raise InvariantViolationError(f"Task {task_id} already has current lease {current['current_lease_id']}")
        conn.execute(
            """
            INSERT INTO leases (
                lease_id, task_id, worker_id, state, issued_at, accepted_at,
                ended_at, replacement_lease_id, intervention_reason, evidence_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lease_id,
                task_id,
                evaluation.selected_worker_id,
                "pending_accept",
                timestamp,
                None,
                None,
                None,
                None,
                decision["decision_id"],
            ),
        )
        conn.execute(
            """
            UPDATE tasks
            SET state = 'reserved', current_worker_id = ?, current_lease_id = ?, routing_policy_ref = ?
            WHERE task_id = ?
            """,
            (evaluation.selected_worker_id, lease_id, evaluation.policy_version, task_id),
        )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    locks = reserve_locks_for_task(
        state_db,
        events_ndjson,
        task_id=task_id,
        lease_id=lease_id,
        protected_surfaces=task["protected_surfaces"],
        policy_origin=evaluation.policy_version,
    )
    assigned = inspect_task(state_db, task_id)
    return {
        "task": assigned,
        "selected_worker_id": evaluation.selected_worker_id,
        "lease_id": lease_id,
        "routing_decision": decision,
        "locks": locks,
    }


def _row_to_task(row) -> dict[str, object]:
    return {
        "task_id": row["task_id"],
        "summary": row["title"],
        "workflow_class": row["workflow_class"],
        "required_capabilities": json.loads(row["required_capabilities"] or "[]"),
        "protected_surfaces": json.loads(row["protected_surfaces"] or "[]"),
        "priority": row["priority"],
        "state": row["state"],
        "current_worker_id": row["current_worker_id"],
        "current_lease_id": row["current_lease_id"],
        "routing_policy_ref": row["routing_policy_ref"],
    }
