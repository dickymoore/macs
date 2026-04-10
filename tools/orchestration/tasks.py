#!/usr/bin/env python3
"""Task creation, inspection, and assignment helpers."""

from __future__ import annotations

import getpass
import json
import os
import socket
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.adapters.registry import get_adapter
from tools.orchestration.config import adapter_settings_path
from tools.orchestration.history import inspect_lease, list_aggregate_events
from tools.orchestration.interventions import (
    build_runtime_pause_resume_status,
    intervention_blocking_condition,
    intervention_next_action,
    runtime_intervention_warnings,
)
from tools.orchestration.invariants import InvariantViolationError, transition_lease_state, transition_task_state
from tools.orchestration.locks import (
    activate_locks_for_task,
    LockConflictError,
    check_lock_conflicts,
    release_locks_for_task,
    reserve_locks_for_task,
)
from tools.orchestration.policy import apply_audit_content_policy, governance_policy_path, load_governance_policy
from tools.orchestration.recovery import (
    abandon_recovery_run,
    complete_recovery_run,
    ensure_recovery_run,
    get_latest_recovery_run,
    get_unresolved_recovery_run,
    inspect_recovery_context,
)
from tools.orchestration.routing import (
    RoutingError,
    evaluate_task_routing,
    inspect_routing_decision,
    persist_routing_decision,
    routing_blocking_condition,
    routing_next_action,
)
from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction
from tools.orchestration.workers import inspect_worker


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def operator_actor_id() -> str:
    explicit = os.environ.get("MACS_OPERATOR_ID")
    if explicit:
        return explicit
    return f"{getpass.getuser()}@{socket.gethostname()}"


def normalized_intervention_rationale(action: str, rationale: str | None) -> str:
    text = (rationale or "").strip()
    if text:
        return text
    return f"operator_requested_{action}"


def record_intervention_decision(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    decision_action: str,
    rationale: str | None,
    lease_id: str | None = None,
    worker_id: str | None = None,
    recovery_run_id: str | None = None,
) -> dict[str, object]:
    intervention_rationale = normalized_intervention_rationale(decision_action, rationale)
    payload = {
        "decision_action": decision_action,
        "decision_class": "operator_confirmed",
        "intervention_rationale": intervention_rationale,
        "affected_refs": {
            "task_id": task_id,
            "lease_id": lease_id,
            "worker_id": worker_id,
            "recovery_run_id": recovery_run_id,
        },
    }
    event = EventRecord(
        event_id=f"evt-intervention-decision-{uuid.uuid4().hex[:12]}",
        event_type="intervention.decision_recorded",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=utc_now(),
        actor_type="operator",
        actor_id=operator_actor_id(),
        correlation_id=f"corr-intervention-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload=payload,
        redaction_level="none",
    )
    write_eventful_transaction(state_db, events_ndjson, event, lambda conn: None)
    return {
        "event": event.as_export(),
        "intervention_rationale": intervention_rationale,
    }


class TaskNotFoundError(RuntimeError):
    """Raised when a requested task does not exist."""


class TaskActionError(RuntimeError):
    """Raised when a task action must return a structured controller error."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        exit_code: int,
        result: dict[str, object] | None = None,
        event: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.result = result or {}
        self.event = event


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
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
        },
        "event": event.as_export(),
    }


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


def inspect_task_context(state_db: Path, task_id: str) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    current_owner = inspect_worker(state_db, task["current_worker_id"]) if task["current_worker_id"] else None
    current_lease = inspect_lease(state_db, task["current_lease_id"]) if task["current_lease_id"] else None
    routing_decision = task.get("routing_decision")
    recovery = inspect_recovery_context(state_db, task_id=task_id)
    adapter_evidence, adapter_probe_warning = _probe_worker_evidence(current_owner)
    task["adapter_evidence"] = adapter_evidence
    if adapter_probe_warning is not None:
        task["adapter_probe_warning"] = adapter_probe_warning
    task["runtime_intervention"] = (
        build_runtime_pause_resume_status(current_owner, action="pause")
        if current_owner is not None and current_lease is not None and current_lease["state"] == "paused"
        else None
    )
    task["blocking_condition"] = recovery.get("blocking_condition")
    task["next_action"] = recovery.get("next_action")
    if (
        task["state"] == "pending_assignment"
        and routing_decision is not None
        and routing_decision.get("selected_worker_id") is None
        and task["blocking_condition"] is None
    ):
        rejected_workers = routing_decision["rationale"].get("rejected_workers", [])
        task["blocking_condition"] = routing_blocking_condition(rejected_workers)
        task["next_action"] = routing_next_action(
            task_id=task["task_id"],
            rejected_workers=rejected_workers,
            governance_policy_path=routing_decision["rationale"].get("governance_policy_path"),
            adapter_settings_path=str(adapter_settings_path(state_db.parent)),
        )

    conn = connect_state_db(state_db)
    try:
        lock_rows = conn.execute(
            """
            SELECT lock_id, target_ref, mode, state, task_id, lease_id
            FROM locks
            WHERE task_id = ? AND state IN ('reserved', 'held')
            ORDER BY lock_id
            """,
            (task_id,),
        ).fetchall()
    finally:
        conn.close()

    task["controller_truth"] = {
        "canonical_state": task["state"],
        "current_owner": (
            {
                "worker_id": current_owner["worker_id"],
                "state": current_owner["state"],
                "runtime_type": current_owner["runtime_type"],
                "adapter_id": current_owner["adapter_id"],
            }
            if current_owner is not None
            else None
        ),
        "current_lease": current_lease,
        "pane_target": (
            {
                "tmux_socket": current_owner["tmux_socket"],
                "tmux_session": current_owner["tmux_session"],
                "tmux_pane": current_owner["tmux_pane"],
            }
            if current_owner is not None
            else None
        ),
        "routing_rationale_summary": (
            {
                "decision_id": routing_decision["decision_id"],
                "selected_worker_id": routing_decision["selected_worker_id"] or "none",
                "rationale": (
                    routing_decision["rationale"].get("summary")
                    or (
                        routing_blocking_condition(routing_decision["rationale"].get("rejected_workers", []))
                        if routing_decision["selected_worker_id"] is None
                        else ""
                    )
                ),
            }
            if routing_decision is not None
            else None
        ),
        "recovery_run": recovery.get("recovery_run"),
        "lock_summary": {
            "active_lock_count": len(lock_rows),
            "locks": [
                {
                    "lock_id": row["lock_id"],
                    "target_ref": row["target_ref"],
                    "mode": row["mode"],
                    "state": row["state"],
                    "task_id": row["task_id"],
                    "lease_id": row["lease_id"],
                }
                for row in lock_rows
            ],
        },
        "recent_event_refs": list_aggregate_events(state_db, task_id),
    }
    return task


def _probe_worker_evidence(worker: dict[str, object] | None) -> tuple[list[dict[str, object]], str | None]:
    if worker is None:
        return [], None
    try:
        return get_adapter(worker["adapter_id"]).probe(worker), None
    except RuntimeError as exc:
        return [], str(exc)


def assign_task(
    repo_root: Path,
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    explicit_worker_id: str | None = None,
    workflow_class: str | None = None,
) -> dict[str, object]:
    return _assign_task_impl(
        repo_root,
        state_db,
        events_ndjson,
        task_id=task_id,
        explicit_worker_id=explicit_worker_id,
        workflow_class=workflow_class,
        enforce_assignments_allowed=True,
        rollback_task_state="pending_assignment",
        allow_unresolved_recovery=False,
    )


def reroute_task(
    repo_root: Path,
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    explicit_worker_id: str | None = None,
    workflow_class: str | None = None,
    rationale: str | None = None,
    decision_context: dict[str, object] | None = None,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    if task["state"] not in {"intervention_hold", "reconciliation"}:
        raise InvariantViolationError(f"Task {task_id} is not reroutable from state {task['state']}")
    if task["current_lease_id"] is None or task["current_worker_id"] is None:
        raise InvariantViolationError(f"Task {task_id} cannot reroute without a predecessor lease")

    predecessor_lease = inspect_lease(state_db, task["current_lease_id"])
    if predecessor_lease["state"] not in {"active", "paused", "suspended", "expiring"}:
        raise InvariantViolationError(
            f"Task {task_id} cannot reroute predecessor lease {predecessor_lease['lease_id']} from state {predecessor_lease['state']}"
        )
    ensure_recovery_run(
        state_db,
        task_id=task_id,
        proposed_worker_id=explicit_worker_id,
        proposed_workflow_class=workflow_class,
    )

    decision = decision_context or record_intervention_decision(
        state_db,
        events_ndjson,
        task_id=task_id,
        decision_action="reroute",
        rationale=rationale,
        lease_id=task["current_lease_id"],
        worker_id=task["current_worker_id"],
    )

    correlation_id = str(decision["event"]["correlation_id"])
    timestamp = utc_now()
    if task["state"] == "intervention_hold":
        reconciliation_event = EventRecord(
            event_id=f"evt-task-reconciliation-{uuid.uuid4().hex[:12]}",
            event_type="task.reconciliation_started",
            aggregate_type="task",
            aggregate_id=task_id,
            timestamp=timestamp,
            actor_type="controller",
            actor_id="controller-main",
            correlation_id=correlation_id,
            causation_id=str(decision["event"]["event_id"]),
            payload={
                "task_id": task_id,
                "predecessor_lease_id": predecessor_lease["lease_id"],
                "predecessor_worker_id": predecessor_lease["worker_id"],
                "reason": predecessor_lease.get("intervention_reason") or "reroute_requested",
                "decision_event_id": decision["event"]["event_id"],
                "intervention_rationale": decision["intervention_rationale"],
            },
            redaction_level="none",
        )
        transition_task_state(
            state_db,
            events_ndjson,
            task_id,
            "reconciliation",
            reconciliation_event,
        )

    revoke_event = EventRecord(
        event_id=f"evt-lease-revoke-{uuid.uuid4().hex[:12]}",
        event_type="lease.revoked",
        aggregate_type="lease",
        aggregate_id=predecessor_lease["lease_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=str(decision["event"]["event_id"]),
        payload={
            "task_id": task_id,
            "lease_id": predecessor_lease["lease_id"],
            "worker_id": predecessor_lease["worker_id"],
            "reason": predecessor_lease.get("intervention_reason") or "reroute_requested",
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        predecessor_lease["lease_id"],
        "revoked",
        timestamp,
        None,
        revoke_event,
    )
    released_locks = release_locks_for_task(
        state_db,
        events_ndjson,
        task_id=task_id,
        lease_id=predecessor_lease["lease_id"],
        correlation_id=correlation_id,
        causation_id=revoke_event.event_id,
        event_metadata={
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
    )
    assignment = _assign_task_impl(
        repo_root,
        state_db,
        events_ndjson,
        task_id=task_id,
        explicit_worker_id=explicit_worker_id,
        workflow_class=workflow_class,
        enforce_assignments_allowed=False,
        rollback_task_state="pending_assignment",
        allow_unresolved_recovery=True,
        correlation_id_override=correlation_id,
        causation_id_override=revoke_event.event_id,
        intervention_metadata={
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
    )
    successor_lease_id = str(assignment["result"]["lease_id"])
    replace_event = EventRecord(
        event_id=f"evt-lease-replaced-{uuid.uuid4().hex[:12]}",
        event_type="lease.replaced",
        aggregate_type="lease",
        aggregate_id=predecessor_lease["lease_id"],
        timestamp=utc_now(),
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=assignment["event"]["event_id"],
        payload={
            "task_id": task_id,
            "lease_id": predecessor_lease["lease_id"],
            "replacement_lease_id": successor_lease_id,
            "previous_worker_id": predecessor_lease["worker_id"],
            "next_worker_id": assignment["result"]["selected_worker_id"],
            "released_lock_ids": [lock["lock_id"] for lock in released_locks],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        predecessor_lease["lease_id"],
        "replaced",
        timestamp,
        successor_lease_id,
        replace_event,
    )

    reroute_event = EventRecord(
        event_id=f"evt-task-reroute-{uuid.uuid4().hex[:12]}",
        event_type="task.rerouted",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=utc_now(),
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=replace_event.event_id,
        payload={
            "task_id": task_id,
            "previous_lease_id": predecessor_lease["lease_id"],
            "replacement_lease_id": successor_lease_id,
            "previous_worker_id": predecessor_lease["worker_id"],
            "selected_worker_id": assignment["result"]["selected_worker_id"],
            "released_lock_ids": [lock["lock_id"] for lock in released_locks],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    write_eventful_transaction(state_db, events_ndjson, reroute_event, lambda conn: None)
    complete_recovery_run(
        state_db,
        task_id=task_id,
        replacement_lease_id=successor_lease_id,
        selected_worker_id=str(assignment["result"]["selected_worker_id"]),
    )
    assignment["result"]["previous_lease_id"] = predecessor_lease["lease_id"]
    assignment["result"]["released_locks"] = released_locks
    assignment["result"]["controller_state_changed"] = True
    assignment["result"]["next_action"] = f"macs task inspect --task {task_id}"
    assignment["result"]["lease"] = inspect_lease(state_db, successor_lease_id)
    assignment["event"] = reroute_event.as_export()
    return assignment


def _assign_task_impl(
    repo_root: Path,
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    explicit_worker_id: str | None = None,
    workflow_class: str | None = None,
    enforce_assignments_allowed: bool,
    rollback_task_state: str,
    allow_unresolved_recovery: bool,
    correlation_id_override: str | None = None,
    causation_id_override: str | None = None,
    intervention_metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    if enforce_assignments_allowed:
        _ensure_assignments_allowed(state_db)
    task = inspect_task(state_db, task_id)
    if not allow_unresolved_recovery:
        _ensure_no_unresolved_interrupted_recovery(state_db, task=task)
    routing_task = dict(task)
    if workflow_class is not None:
        routing_task["workflow_class"] = workflow_class
    evaluation = evaluate_task_routing(repo_root, state_db, routing_task, explicit_worker_id=explicit_worker_id)
    if evaluation.selected_worker_id is None:
        decision = persist_routing_decision(
            state_db,
            events_ndjson,
            task_id,
            evaluation,
            lock_check_result={"ok": None, "skipped": "no_eligible_worker"},
        )
        raise TaskActionError(
            "No eligible workers for task",
            code="policy_blocked",
            exit_code=4,
            result={
                "routing_decision": decision,
                "routing_evaluation": evaluation.as_dict(),
                "controller_state_changed": False,
                "blocking_condition": routing_blocking_condition(evaluation.rejected_workers),
                "next_action": routing_next_action(
                    task_id=task_id,
                    rejected_workers=evaluation.rejected_workers,
                    governance_policy_path=evaluation.governance_policy_path,
                    adapter_settings_path=str(adapter_settings_path(repo_root / ".codex" / "orchestration")),
                ),
            },
        )
    lock_check = check_lock_conflicts(state_db, task["protected_surfaces"])
    if not lock_check["ok"]:
        raise LockConflictError(json.dumps(lock_check["conflicts"], sort_keys=True))

    decision = persist_routing_decision(state_db, events_ndjson, task_id, evaluation, lock_check_result=lock_check)
    governance_policy = load_governance_policy(governance_policy_path(repo_root / ".codex" / "orchestration"))
    lease_id = f"lease-{uuid.uuid4().hex[:12]}"
    timestamp = utc_now()
    governed_audit_content, redaction_level = apply_audit_content_policy(
        governance_policy,
        rich_content={"prompt_content": assignment_payload_for_task(task=task, routing_task=routing_task, lease_id=lease_id, worker_id=evaluation.selected_worker_id)},
    )
    event = EventRecord(
        event_id=f"evt-task-assign-{uuid.uuid4().hex[:12]}",
        event_type="task.assigned",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id_override or f"corr-task-assign-{uuid.uuid4().hex[:12]}",
        causation_id=causation_id_override or decision["decision_id"],
        payload={
            "task_id": task_id,
            "worker_id": evaluation.selected_worker_id,
            "lease_id": lease_id,
            "routing_decision_id": decision["decision_id"],
            "governance_policy_version": governance_policy["policy_version"],
            "audit_content": governed_audit_content,
            **(intervention_metadata or {}),
        },
        redaction_level=redaction_level,
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
        correlation_id=event.correlation_id,
        causation_id=event.event_id,
        event_metadata=intervention_metadata,
    )
    worker = inspect_worker(state_db, evaluation.selected_worker_id)
    adapter = get_adapter(worker["adapter_id"])
    assignment_payload = assignment_payload_for_task(
        task=task,
        routing_task=routing_task,
        lease_id=lease_id,
        worker_id=evaluation.selected_worker_id,
    )
    try:
        dispatch_result = adapter.dispatch(worker, assignment_payload)
        if not dispatch_result.get("ok"):
            raise RuntimeError(f"Assignment dispatch failed for task {task_id}")
        ack = adapter.acknowledge_delivery(worker, event.correlation_id)
        if not ack.get("ok"):
            raise RuntimeError(f"Assignment delivery acknowledgment failed for task {task_id}")
    except RuntimeError as exc:
        failure = _rollback_assignment_side_effect_failure(
            state_db,
            events_ndjson,
            task_id=task_id,
            lease_id=lease_id,
            worker_id=evaluation.selected_worker_id,
            correlation_id=event.correlation_id,
            message=str(exc),
            rollback_task_state=rollback_task_state,
        )
        raise TaskActionError(
            f"Assignment side effect failed for task {task_id}: {exc}",
            code="side_effect_failed",
            exit_code=6,
            result=failure["result"],
            event=failure["event"],
        ) from exc

    activation_timestamp = ack.get("acknowledged_at", utc_now())
    lease_event = EventRecord(
        event_id=f"evt-lease-activate-{uuid.uuid4().hex[:12]}",
        event_type="lease.activated",
        aggregate_type="lease",
        aggregate_id=lease_id,
        timestamp=activation_timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=event.correlation_id,
        causation_id=event.event_id,
        payload={
            "task_id": task_id,
            "lease_id": lease_id,
            "worker_id": evaluation.selected_worker_id,
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        lease_id,
        "active",
        None,
        None,
        lease_event,
        accepted_at=activation_timestamp,
    )
    locks = activate_locks_for_task(
        state_db,
        events_ndjson,
        task_id=task_id,
        lease_id=lease_id,
        correlation_id=event.correlation_id,
        causation_id=lease_event.event_id,
        event_metadata=intervention_metadata,
    )
    task_event = EventRecord(
        event_id=f"evt-task-activate-{uuid.uuid4().hex[:12]}",
        event_type="task.activated",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=activation_timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=event.correlation_id,
        causation_id=lease_event.event_id,
        payload={
            "task_id": task_id,
            "lease_id": lease_id,
            "worker_id": evaluation.selected_worker_id,
        },
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "active",
        task_event,
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "selected_worker_id": evaluation.selected_worker_id,
            "lease_id": lease_id,
            "routing_decision": decision,
            "locks": locks,
        },
        "event": event.as_export(),
    }


def assignment_payload_for_task(
    *,
    task: dict[str, object],
    routing_task: dict[str, object],
    lease_id: str,
    worker_id: str,
) -> str:
    return (
        "MACS_TASK_ASSIGN "
        + json.dumps(
            {
                "task_id": task["task_id"],
                "summary": task["summary"],
                "workflow_class": routing_task["workflow_class"],
                "lease_id": lease_id,
                "worker_id": worker_id,
            },
            sort_keys=True,
        )
    )


def retry_task_recovery(
    repo_root: Path,
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    rationale: str | None = None,
) -> dict[str, object]:
    recovery_run = get_unresolved_recovery_run(state_db, task_id=task_id)
    if recovery_run is None:
        raise TaskActionError(
            f"Task {task_id} has no unresolved recovery run to retry",
            code="not_found",
            exit_code=3,
        )

    decision_summary = recovery_run["decision_summary"]
    explicit_worker_id = decision_summary.get("proposed_worker_id")
    workflow_class = decision_summary.get("proposed_workflow_class")
    if explicit_worker_id is None and workflow_class is None:
        raise TaskActionError(
            f"Recovery run {recovery_run['recovery_run_id']} does not record a continuation target",
            code="conflict",
            exit_code=4,
        )

    task = inspect_task(state_db, task_id)
    decision = record_intervention_decision(
        state_db,
        events_ndjson,
        task_id=task_id,
        decision_action="recovery_retry",
        rationale=rationale,
        lease_id=task["current_lease_id"],
        worker_id=task["current_worker_id"],
        recovery_run_id=str(recovery_run["recovery_run_id"]),
    )
    timestamp = utc_now()
    retry_event = EventRecord(
        event_id=f"evt-recovery-retry-{uuid.uuid4().hex[:12]}",
        event_type="recovery.retry_requested",
        aggregate_type="recovery",
        aggregate_id=recovery_run["recovery_run_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=str(decision["event"]["correlation_id"]),
        causation_id=str(decision["event"]["event_id"]),
        payload={
            "task_id": task_id,
            "recovery_run_id": recovery_run["recovery_run_id"],
            "proposed_worker_id": explicit_worker_id,
            "proposed_workflow_class": workflow_class,
            "task_state": task["state"],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    write_eventful_transaction(state_db, events_ndjson, retry_event, lambda conn: None)

    if task["current_lease_id"] is not None and task["current_worker_id"] is not None:
        action = reroute_task(
            repo_root,
            state_db,
            events_ndjson,
            task_id=task_id,
            explicit_worker_id=explicit_worker_id,
            workflow_class=workflow_class,
            decision_context=decision,
        )
    else:
        action = _assign_task_impl(
            repo_root,
            state_db,
            events_ndjson,
            task_id=task_id,
            explicit_worker_id=explicit_worker_id,
            workflow_class=workflow_class,
            enforce_assignments_allowed=False,
            rollback_task_state=task["state"],
            allow_unresolved_recovery=True,
            correlation_id_override=str(decision["event"]["correlation_id"]),
            causation_id_override=retry_event.event_id,
            intervention_metadata={
                "decision_event_id": decision["event"]["event_id"],
                "intervention_rationale": decision["intervention_rationale"],
            },
        )
        lease_id = str(action["result"]["lease_id"])
        complete_recovery_run(
            state_db,
            task_id=task_id,
            replacement_lease_id=lease_id,
            selected_worker_id=str(action["result"]["selected_worker_id"]),
        )
        action["result"]["lease"] = inspect_lease(state_db, lease_id)
        action["result"]["controller_state_changed"] = True
        action["result"]["next_action"] = f"macs task inspect --task {task_id}"

    return {
        "result": action["result"],
        "event": retry_event.as_export(),
        "recovery_run": get_latest_recovery_run(state_db, task_id=task_id),
        "warnings": action.get("warnings", []),
    }


def reconcile_task_recovery(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    rationale: str | None = None,
) -> dict[str, object]:
    recovery_run = get_unresolved_recovery_run(state_db, task_id=task_id)
    if recovery_run is None:
        raise TaskActionError(
            f"Task {task_id} has no unresolved recovery run to reconcile",
            code="not_found",
            exit_code=3,
        )

    decision = record_intervention_decision(
        state_db,
        events_ndjson,
        task_id=task_id,
        decision_action="recovery_reconcile",
        rationale=rationale,
        lease_id=inspect_task(state_db, task_id)["current_lease_id"],
        worker_id=inspect_task(state_db, task_id)["current_worker_id"],
        recovery_run_id=str(recovery_run["recovery_run_id"]),
    )
    updated_run = abandon_recovery_run(state_db, task_id=task_id)
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-recovery-reconcile-{uuid.uuid4().hex[:12]}",
        event_type="recovery.reconciled",
        aggregate_type="recovery",
        aggregate_id=recovery_run["recovery_run_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=str(decision["event"]["correlation_id"]),
        causation_id=str(decision["event"]["event_id"]),
        payload={
            "task_id": task_id,
            "recovery_run_id": recovery_run["recovery_run_id"],
            "outcome": "abandoned",
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    write_eventful_transaction(state_db, events_ndjson, event, lambda conn: None)
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "controller_state_changed": True,
            "next_action": f"macs task inspect --task {task_id}",
        },
        "event": event.as_export(),
        "recovery_run": updated_run,
        "warnings": [],
    }


def close_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    if task["state"] != "active":
        raise InvariantViolationError(f"Task {task_id} is not closable from state {task['state']}")
    if task["current_lease_id"] is None:
        raise InvariantViolationError(f"Task {task_id} cannot close without a live lease")

    timestamp = utc_now()
    correlation_id = f"corr-task-close-{uuid.uuid4().hex[:12]}"
    lease_event = EventRecord(
        event_id=f"evt-lease-complete-{uuid.uuid4().hex[:12]}",
        event_type="lease.completed",
        aggregate_type="lease",
        aggregate_id=task["current_lease_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=None,
        payload={
            "task_id": task_id,
            "lease_id": task["current_lease_id"],
            "worker_id": task["current_worker_id"],
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        task["current_lease_id"],
        "completed",
        timestamp,
        None,
        lease_event,
    )
    released_locks = release_locks_for_task(
        state_db,
        events_ndjson,
        task_id=task_id,
        lease_id=task["current_lease_id"],
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
    )

    task_event = EventRecord(
        event_id=f"evt-task-complete-{uuid.uuid4().hex[:12]}",
        event_type="task.completed",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=None,
        payload={
            "task_id": task_id,
            "lease_id": task["current_lease_id"],
            "released_lock_ids": [lock["lock_id"] for lock in released_locks],
        },
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "completed",
        task_event,
    )

    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "lease": inspect_lease(state_db, task["current_lease_id"]),
            "locks": released_locks,
        },
        "event": task_event.as_export(),
    }


def pause_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    rationale: str | None = None,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    if task["state"] != "active":
        raise InvariantViolationError(f"Task {task_id} is not pausable from state {task['state']}")
    if task["current_lease_id"] is None or task["current_worker_id"] is None:
        raise InvariantViolationError(f"Task {task_id} cannot pause without a live lease")

    lease = inspect_lease(state_db, task["current_lease_id"])
    if lease["state"] != "active":
        raise InvariantViolationError(f"Task {task_id} cannot pause lease {lease['lease_id']} from state {lease['state']}")

    worker = inspect_worker(state_db, task["current_worker_id"])
    runtime_intervention = build_runtime_pause_resume_status(worker, action="pause")
    decision = record_intervention_decision(
        state_db,
        events_ndjson,
        task_id=task_id,
        decision_action="pause",
        rationale=rationale,
        lease_id=lease["lease_id"],
        worker_id=task["current_worker_id"],
    )
    timestamp = utc_now()
    correlation_id = str(decision["event"]["correlation_id"])
    lease_event = EventRecord(
        event_id=f"evt-lease-pause-{uuid.uuid4().hex[:12]}",
        event_type="lease.paused",
        aggregate_type="lease",
        aggregate_id=lease["lease_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=str(decision["event"]["event_id"]),
        payload={
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "worker_id": task["current_worker_id"],
            "intervention_reason": "operator_pause",
            "runtime_intervention_status": runtime_intervention["status"],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        lease["lease_id"],
        "paused",
        None,
        None,
        lease_event,
        intervention_reason="operator_pause",
    )
    task_event = EventRecord(
        event_id=f"evt-task-pause-{uuid.uuid4().hex[:12]}",
        event_type="task.paused",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
        payload={
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "worker_id": task["current_worker_id"],
            "intervention_reason": "operator_pause",
            "runtime_intervention_status": runtime_intervention["status"],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "intervention_hold",
        task_event,
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "lease": inspect_lease(state_db, lease["lease_id"]),
            "runtime_intervention": runtime_intervention,
            "controller_state_changed": True,
            "next_action": f"macs task inspect --task {task_id}",
        },
        "event": task_event.as_export(),
        "warnings": runtime_intervention_warnings(runtime_intervention),
    }


def freeze_task_for_risk(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    intervention_reason: str,
    evidence_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    if task["state"] != "active":
        raise InvariantViolationError(f"Task {task_id} is not freezable from state {task['state']}")
    if task["current_lease_id"] is None or task["current_worker_id"] is None:
        raise InvariantViolationError(f"Task {task_id} cannot freeze without a live lease")

    lease = inspect_lease(state_db, task["current_lease_id"])
    if lease["state"] not in {"active", "expiring"}:
        raise InvariantViolationError(
            f"Task {task_id} cannot freeze lease {lease['lease_id']} from state {lease['state']}"
        )

    timestamp = utc_now()
    correlation_id = f"corr-task-risk-freeze-{uuid.uuid4().hex[:12]}"
    payload = {
        "task_id": task_id,
        "lease_id": lease["lease_id"],
        "worker_id": task["current_worker_id"],
        "intervention_reason": intervention_reason,
    }
    if evidence_summary:
        payload["evidence_summary"] = evidence_summary

    lease_event = EventRecord(
        event_id=f"evt-lease-suspend-{uuid.uuid4().hex[:12]}",
        event_type="lease.suspended",
        aggregate_type="lease",
        aggregate_id=lease["lease_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=None,
        payload=payload,
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        lease["lease_id"],
        "suspended",
        None,
        None,
        lease_event,
        intervention_reason=intervention_reason,
    )
    task_event = EventRecord(
        event_id=f"evt-task-risk-hold-{uuid.uuid4().hex[:12]}",
        event_type="task.risk_hold_applied",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
        payload=payload,
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "intervention_hold",
        task_event,
    )
    ensure_recovery_run(
        state_db,
        task_id=task_id,
        proposed_workflow_class=str(task["workflow_class"]),
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "lease": inspect_lease(state_db, lease["lease_id"]),
            "controller_state_changed": True,
            "next_action": f"macs task inspect --task {task_id}",
        },
        "event": task_event.as_export(),
        "warnings": [],
    }


def freeze_owned_active_tasks_for_worker(
    state_db: Path,
    events_ndjson: Path,
    *,
    worker_id: str,
    worker_state: str,
    evidence_summary: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        task_rows = conn.execute(
            """
            SELECT task_id
            FROM tasks
            WHERE current_worker_id = ? AND state = 'active'
            ORDER BY task_id
            """,
            (worker_id,),
        ).fetchall()
    finally:
        conn.close()

    frozen = []
    for row in task_rows:
        frozen.append(
            freeze_task_for_risk(
                state_db,
                events_ndjson,
                task_id=row["task_id"],
                intervention_reason=f"worker_state_{worker_state}",
                evidence_summary=evidence_summary,
            )
        )
    return frozen


def resume_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    if task["state"] != "intervention_hold":
        raise InvariantViolationError(f"Task {task_id} is not resumable from state {task['state']}")
    if task["current_lease_id"] is None or task["current_worker_id"] is None:
        raise InvariantViolationError(f"Task {task_id} cannot resume without a live lease")

    lease = inspect_lease(state_db, task["current_lease_id"])
    if lease["state"] != "paused":
        raise InvariantViolationError(
            f"Task {task_id} cannot resume lease {lease['lease_id']} from state {lease['state']}"
        )

    worker = inspect_worker(state_db, task["current_worker_id"])
    _ensure_resume_allowed(state_db, task_id=task_id, worker=worker)
    runtime_intervention = build_runtime_pause_resume_status(worker, action="resume")
    decision = record_intervention_decision(
        state_db,
        events_ndjson,
        task_id=task_id,
        decision_action="resume",
        rationale=None,
        lease_id=lease["lease_id"],
        worker_id=task["current_worker_id"],
    )
    timestamp = utc_now()
    correlation_id = str(decision["event"]["correlation_id"])
    lease_event = EventRecord(
        event_id=f"evt-lease-resume-{uuid.uuid4().hex[:12]}",
        event_type="lease.resumed",
        aggregate_type="lease",
        aggregate_id=lease["lease_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=str(decision["event"]["event_id"]),
        payload={
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "worker_id": task["current_worker_id"],
            "intervention_reason": lease.get("intervention_reason"),
            "runtime_intervention_status": runtime_intervention["status"],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        lease["lease_id"],
        "active",
        None,
        None,
        lease_event,
        intervention_reason=None,
    )
    task_event = EventRecord(
        event_id=f"evt-task-resume-{uuid.uuid4().hex[:12]}",
        event_type="task.resumed",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
        payload={
            "task_id": task_id,
            "lease_id": lease["lease_id"],
            "worker_id": task["current_worker_id"],
            "runtime_intervention_status": runtime_intervention["status"],
            "decision_event_id": decision["event"]["event_id"],
            "intervention_rationale": decision["intervention_rationale"],
        },
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "active",
        task_event,
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "lease": inspect_lease(state_db, lease["lease_id"]),
            "runtime_intervention": runtime_intervention,
            "controller_state_changed": True,
            "next_action": f"macs task inspect --task {task_id}",
        },
        "event": task_event.as_export(),
        "warnings": runtime_intervention_warnings(runtime_intervention),
    }


def _rollback_assignment_side_effect_failure(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
    lease_id: str,
    worker_id: str,
    correlation_id: str,
    message: str,
    rollback_task_state: str,
) -> dict[str, object]:
    timestamp = utc_now()
    lease_event = EventRecord(
        event_id=f"evt-lease-revoke-{uuid.uuid4().hex[:12]}",
        event_type="lease.revoked",
        aggregate_type="lease",
        aggregate_id=lease_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=None,
        payload={"task_id": task_id, "lease_id": lease_id, "worker_id": worker_id, "reason": message},
        redaction_level="none",
    )
    transition_lease_state(
        state_db,
        events_ndjson,
        lease_id,
        "revoked",
        timestamp,
        None,
        lease_event,
    )
    released_locks = release_locks_for_task(
        state_db,
        events_ndjson,
        task_id=task_id,
        lease_id=lease_id,
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
    )
    task_event = EventRecord(
        event_id=f"evt-task-assign-failed-{uuid.uuid4().hex[:12]}",
        event_type="task.assignment_failed",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=correlation_id,
        causation_id=lease_event.event_id,
        payload={
            "task_id": task_id,
            "lease_id": lease_id,
            "worker_id": worker_id,
            "message": message,
            "released_lock_ids": [lock["lock_id"] for lock in released_locks],
        },
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        rollback_task_state,
        task_event,
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
            "lease": inspect_lease(state_db, lease_id),
            "locks": released_locks,
        },
        "event": task_event.as_export(),
    }


def archive_task(
    state_db: Path,
    events_ndjson: Path,
    *,
    task_id: str,
) -> dict[str, object]:
    task = inspect_task(state_db, task_id)
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-task-archive-{uuid.uuid4().hex[:12]}",
        event_type="task.archived",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-task-archive-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload={"task_id": task_id, "from_state": task["state"]},
        redaction_level="none",
    )
    transition_task_state(
        state_db,
        events_ndjson,
        task_id,
        "archived",
        event,
    )
    return {
        "result": {
            "task": inspect_task(state_db, task_id),
        },
        "event": event.as_export(),
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


def _ensure_assignments_allowed(state_db: Path) -> None:
    if _metadata_value(state_db, "assignments_blocked") == "1":
        raise RoutingError("Assignments are blocked pending startup recovery reconciliation")


def _ensure_no_unresolved_interrupted_recovery(
    state_db: Path,
    *,
    task: dict[str, object],
) -> None:
    if task["current_lease_id"] is not None:
        return
    recovery_run = get_unresolved_recovery_run(state_db, task_id=str(task["task_id"]))
    if recovery_run is None:
        return
    raise TaskActionError(
        "Task "
        f"{task['task_id']} has unresolved interrupted recovery run {recovery_run['recovery_run_id']}. "
        f"Inspect with 'macs recovery inspect --task {task['task_id']}' and continue through "
        "'macs recovery retry --task {task['task_id']}' or "
        f"'macs recovery reconcile --task {task['task_id']}' before assigning a successor.",
        code="degraded_precondition",
        exit_code=5,
    )


def _ensure_resume_allowed(
    state_db: Path,
    *,
    task_id: str,
    worker: dict[str, object],
) -> None:
    if _metadata_value(state_db, "assignments_blocked") == "1":
        raise TaskActionError(
            "Task "
            f"{task_id} cannot resume while startup recovery reconciliation is still blocking progress. "
            f"Inspect the task first with 'macs task inspect --task {task_id}' and continue through recovery or reroute.",
            code="degraded_precondition",
            exit_code=5,
        )
    if worker["state"] in {"degraded", "unavailable", "quarantined"}:
        raise TaskActionError(
            "Task "
            f"{task_id} cannot resume while current worker {worker['worker_id']} is {worker['state']}. "
            f"Inspect the task first with 'macs task inspect --task {task_id}' and continue through reroute or recovery.",
            code="degraded_precondition",
            exit_code=5,
        )


def _task_inspect_next_action(
    state_db: Path,
    *,
    task_id: str,
    task_state: str,
    current_owner: dict[str, object] | None,
    current_lease: dict[str, object] | None,
) -> str | None:
    return intervention_next_action(
        task_id=task_id,
        task_state=task_state,
        lease_state=current_lease["state"] if current_lease is not None else None,
        owner_state=current_owner["state"] if current_owner is not None else None,
        assignments_blocked=_metadata_value(state_db, "assignments_blocked") == "1",
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
