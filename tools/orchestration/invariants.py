#!/usr/bin/env python3
"""Task and lease invariant helpers for the authoritative store."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from tools.orchestration.state_machine import (
    LIVE_LEASE_STATES,
    StateTransitionError,
    validate_lease_state,
    validate_lease_transition,
    validate_task_state,
    validate_task_transition,
)
from tools.orchestration.store import EventRecord, write_eventful_transaction


class InvariantViolationError(RuntimeError):
    """Raised when a requested task/lease transition would violate authority rules."""


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    title: str
    description: str
    workflow_class: str
    intent: str
    required_capabilities: list[str]
    protected_surfaces: list[str]
    priority: str
    state: str
    current_worker_id: str | None
    current_lease_id: str | None
    routing_policy_ref: str | None


@dataclass(frozen=True)
class LeaseRecord:
    lease_id: str
    task_id: str
    worker_id: str
    state: str
    issued_at: str
    accepted_at: str | None
    ended_at: str | None
    replacement_lease_id: str | None
    intervention_reason: str | None
    evidence_version: str


def create_task(
    state_db,
    events_ndjson,
    task: TaskRecord,
    event: EventRecord,
) -> None:
    validate_task_state(task.state)

    def mutator(conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            INSERT INTO tasks (
                task_id, title, description, workflow_class, intent,
                required_capabilities, protected_surfaces, priority, state,
                current_worker_id, current_lease_id, routing_policy_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.title,
                task.description,
                task.workflow_class,
                task.intent,
                json.dumps(task.required_capabilities),
                json.dumps(task.protected_surfaces),
                task.priority,
                task.state,
                task.current_worker_id,
                task.current_lease_id,
                task.routing_policy_ref,
            ),
        )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)


def issue_lease(
    state_db,
    events_ndjson,
    lease: LeaseRecord,
    event: EventRecord,
) -> None:
    validate_lease_state(lease.state)

    def mutator(conn: sqlite3.Connection) -> None:
        ensure_task_exists(conn, lease.task_id)
        if lease.state in LIVE_LEASE_STATES:
            current_live = get_live_lease_row(conn, lease.task_id)
            if current_live is not None:
                raise InvariantViolationError(
                    f"Task {lease.task_id} already has live lease {current_live['lease_id']}"
                )

        conn.execute(
            """
            INSERT INTO leases (
                lease_id, task_id, worker_id, state, issued_at, accepted_at,
                ended_at, replacement_lease_id, intervention_reason, evidence_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lease.lease_id,
                lease.task_id,
                lease.worker_id,
                lease.state,
                lease.issued_at,
                lease.accepted_at,
                lease.ended_at,
                lease.replacement_lease_id,
                lease.intervention_reason,
                lease.evidence_version,
            ),
        )
        conn.execute(
            """
            UPDATE tasks
            SET current_worker_id = ?, current_lease_id = ?
            WHERE task_id = ?
            """,
            (
                lease.worker_id if lease.state in LIVE_LEASE_STATES else None,
                lease.lease_id if lease.state in LIVE_LEASE_STATES else None,
                lease.task_id,
            ),
        )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)


def transition_lease_state(
    state_db,
    events_ndjson,
    lease_id: str,
    new_state: str,
    ended_at: str | None,
    replacement_lease_id: str | None,
    event: EventRecord,
) -> None:
    def mutator(conn: sqlite3.Connection) -> None:
        lease = conn.execute(
            "SELECT lease_id, task_id, worker_id, state FROM leases WHERE lease_id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            raise InvariantViolationError(f"Lease {lease_id} does not exist")

        task = conn.execute(
            "SELECT task_id, current_lease_id FROM tasks WHERE task_id = ?",
            (lease["task_id"],),
        ).fetchone()
        if task is None:
            raise InvariantViolationError(f"Task {lease['task_id']} does not exist")

        try:
            validate_lease_transition(lease["state"], new_state)
        except StateTransitionError as exc:
            raise InvariantViolationError(str(exc)) from exc

        if new_state in LIVE_LEASE_STATES:
            current_live = get_live_lease_row(conn, lease["task_id"])
            if current_live is not None and current_live["lease_id"] != lease_id:
                raise InvariantViolationError(
                    f"Task {lease['task_id']} already has live lease {current_live['lease_id']}"
                )

        conn.execute(
            """
            UPDATE leases
            SET state = ?, ended_at = ?, replacement_lease_id = COALESCE(?, replacement_lease_id)
            WHERE lease_id = ?
            """,
            (new_state, ended_at, replacement_lease_id, lease_id),
        )

        if new_state in LIVE_LEASE_STATES:
            conn.execute(
                """
                UPDATE tasks
                SET current_worker_id = ?, current_lease_id = ?
                WHERE task_id = ?
                """,
                (lease["worker_id"], lease_id, lease["task_id"]),
            )
        elif task["current_lease_id"] == lease_id:
            conn.execute(
                """
                UPDATE tasks
                SET current_worker_id = NULL, current_lease_id = NULL
                WHERE task_id = ?
                """,
                (lease["task_id"],),
            )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)


def transition_task_state(
    state_db,
    events_ndjson,
    task_id: str,
    new_state: str,
    event: EventRecord,
) -> None:
    def mutator(conn: sqlite3.Connection) -> None:
        task = conn.execute(
            "SELECT task_id, state FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if task is None:
            raise InvariantViolationError(f"Task {task_id} does not exist")

        try:
            validate_task_transition(task["state"], new_state)
        except StateTransitionError as exc:
            raise InvariantViolationError(str(exc)) from exc

        current_live = get_live_lease_row(conn, task_id)
        if new_state == "active" and current_live is None:
            raise InvariantViolationError(f"Task {task_id} cannot become active without a live lease")
        if new_state in {"completed", "failed", "aborted", "archived"} and current_live is not None:
            raise InvariantViolationError(
                f"Task {task_id} cannot transition to {new_state} while live lease {current_live['lease_id']} exists"
            )

        conn.execute("UPDATE tasks SET state = ? WHERE task_id = ?", (new_state, task_id))

    write_eventful_transaction(state_db, events_ndjson, event, mutator)


def ensure_task_exists(conn: sqlite3.Connection, task_id: str) -> None:
    row = conn.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
    if row is None:
        raise InvariantViolationError(f"Task {task_id} does not exist")


def get_live_lease_row(conn: sqlite3.Connection, task_id: str):
    return conn.execute(
        """
        SELECT lease_id, task_id, worker_id, state
        FROM leases
        WHERE task_id = ? AND state IN ({})
        ORDER BY issued_at DESC, lease_id DESC
        LIMIT 1
        """.format(",".join("?" for _ in LIVE_LEASE_STATES)),
        (task_id, *LIVE_LEASE_STATES),
    ).fetchone()
