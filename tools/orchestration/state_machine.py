#!/usr/bin/env python3
"""Canonical task and lease state vocabularies and transition rules."""

from __future__ import annotations


TASK_STATES = (
    "draft",
    "pending_assignment",
    "reserved",
    "active",
    "intervention_hold",
    "reconciliation",
    "completed",
    "failed",
    "aborted",
    "archived",
)

LEASE_STATES = (
    "pending_accept",
    "active",
    "paused",
    "suspended",
    "expiring",
    "revoked",
    "expired",
    "completed",
    "failed",
    "replaced",
)

LIVE_LEASE_STATES = ("active", "paused", "suspended", "expiring")

TASK_TRANSITIONS = {
    "draft": {"pending_assignment"},
    "pending_assignment": {"reserved"},
    "reserved": {"active", "pending_assignment"},
    "active": {"intervention_hold", "reconciliation", "completed", "failed"},
    "intervention_hold": {"active", "reconciliation"},
    "reconciliation": {"reserved", "failed"},
    "completed": {"archived"},
    "failed": {"archived"},
    "aborted": {"archived"},
    "archived": set(),
}

LEASE_TRANSITIONS = {
    "pending_accept": {"active", "revoked"},
    "active": {"paused", "suspended", "expiring", "completed", "failed", "revoked"},
    "paused": {"active", "revoked"},
    "suspended": {"active", "revoked"},
    "expiring": {"active", "expired"},
    "revoked": {"replaced"},
    "expired": set(),
    "completed": set(),
    "failed": set(),
    "replaced": set(),
}


class StateTransitionError(RuntimeError):
    """Raised when a requested state is invalid or an illegal transition is attempted."""


def validate_task_state(state: str) -> None:
    if state not in TASK_STATES:
        raise StateTransitionError(f"Invalid task state: {state}")


def validate_lease_state(state: str) -> None:
    if state not in LEASE_STATES:
        raise StateTransitionError(f"Invalid lease state: {state}")


def validate_task_transition(current_state: str, new_state: str) -> None:
    validate_task_state(current_state)
    validate_task_state(new_state)
    if new_state not in TASK_TRANSITIONS[current_state]:
        raise StateTransitionError(f"Invalid task transition: {current_state} -> {new_state}")


def validate_lease_transition(current_state: str, new_state: str) -> None:
    validate_lease_state(current_state)
    validate_lease_state(new_state)
    if new_state not in LEASE_TRANSITIONS[current_state]:
        raise StateTransitionError(f"Invalid lease transition: {current_state} -> {new_state}")
