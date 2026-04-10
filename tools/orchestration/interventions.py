#!/usr/bin/env python3
"""Runtime intervention support helpers."""

from __future__ import annotations

from tools.orchestration.adapters.registry import get_adapter

UNSAFE_WORKER_STATES = {"degraded", "unavailable", "quarantined"}


def build_runtime_pause_resume_status(
    worker: dict[str, object] | None,
    *,
    action: str,
) -> dict[str, object] | None:
    if worker is None:
        return None

    descriptor = get_adapter(str(worker["adapter_id"])).descriptor()
    supported_operations = set(descriptor.get("supported_operations", []))
    supports_pause_resume = {"pause", "resume"}.issubset(supported_operations)
    message = None
    status = "runtime_supported"
    if not supports_pause_resume:
        status = "controller_only"
        if action == "resume":
            message = (
                f"Adapter {worker['adapter_id']} does not advertise pause/resume depth; "
                "controller resume restored control-plane state, but live runtime follow-up may still be required."
            )
        else:
            message = (
                f"Adapter {worker['adapter_id']} does not advertise pause/resume depth; "
                "controller state is authoritative and live runtime follow-up may still be required."
            )
    return {
        "action": action,
        "adapter_id": worker["adapter_id"],
        "runtime_type": worker["runtime_type"],
        "status": status,
        "supported": supports_pause_resume,
        "message": message,
    }


def runtime_intervention_warnings(runtime_intervention: dict[str, object] | None) -> list[str]:
    if not isinstance(runtime_intervention, dict):
        return []
    message = runtime_intervention.get("message")
    return [message] if isinstance(message, str) and message else []


def intervention_next_action(
    *,
    task_id: str,
    task_state: str,
    lease_state: str | None,
    owner_state: str | None,
    assignments_blocked: bool,
) -> str | None:
    if task_state != "intervention_hold" or lease_state is None:
        return None
    if lease_state == "suspended":
        return f"reroute or recover task {task_id} before resume"
    if lease_state != "paused":
        return None
    if assignments_blocked:
        return f"resolve startup recovery before resume for task {task_id}"
    if owner_state in UNSAFE_WORKER_STATES:
        return f"reroute or recover task {task_id} before resume"
    return f"macs task resume --task {task_id}"


def intervention_blocking_condition(
    *,
    task_state: str,
    lease_state: str | None,
    owner_state: str | None,
    assignments_blocked: bool,
) -> str | None:
    if task_state != "intervention_hold" or lease_state is None:
        return None
    if assignments_blocked:
        return "startup recovery reconciliation is blocking progress"
    if lease_state == "suspended" and owner_state in UNSAFE_WORKER_STATES:
        return f"current worker is {owner_state}; controller suspended the live lease"
    if lease_state == "suspended":
        return "controller suspended the live lease pending recovery"
    if lease_state == "paused":
        return "operator pause is holding task progression"
    return None
