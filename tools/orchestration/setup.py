#!/usr/bin/env python3
"""Read-only setup validation and dry-run helpers."""

from __future__ import annotations

import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.adapters.registry import list_adapters
from tools.orchestration.config import (
    adapter_configuration,
    adapter_settings_summary,
    load_adapter_settings,
    load_controller_defaults,
    load_state_layout,
    resolved_compatibility_paths,
)
from tools.orchestration.policy import (
    active_governance_snapshot,
    governance_policy_path,
    load_governance_policy,
    load_routing_policy,
    resolve_secret_scopes,
    resolve_surface_version_pins,
    routing_policy_path,
)
from tools.orchestration.workers import list_workers


CORE_DEPENDENCIES = (
    ("python3", "controller_cli"),
    ("tmux", "tmux_worker_discovery"),
)

RUNTIME_BINARY_COMMANDS = {
    "codex": "codex",
    "claude": "claude",
    "gemini": "gemini",
    "local": None,
}

GUIDE_ORIENTATION = {
    "summary": "Controller-owned setup guidance over current repo-local state.",
    "authority_note": "Runtime availability on PATH is a hint; controller facts determine readiness.",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def required_setup_paths(paths) -> list[Path]:
    return [
        paths.controller_defaults_path,
        paths.adapter_settings_path,
        routing_policy_path(paths.orchestration_dir),
        governance_policy_path(paths.orchestration_dir),
        paths.state_layout_path,
        paths.state_db,
        paths.events_ndjson,
    ]


def missing_setup_paths(paths) -> list[str]:
    return [str(path) for path in required_setup_paths(paths) if not path.exists()]


def build_setup_configuration_snapshot(repo_root: Path, paths) -> dict[str, object]:
    controller_defaults = load_controller_defaults(paths.controller_defaults_path)
    adapter_settings = load_adapter_settings(paths.adapter_settings_path)
    routing_policy = load_routing_policy(routing_policy_path(paths.orchestration_dir))
    governance_policy = load_governance_policy(governance_policy_path(paths.orchestration_dir))
    governance_snapshot = active_governance_snapshot(paths.state_db, live_policy=governance_policy)
    state_layout = load_state_layout(paths.state_layout_path)
    compatibility_paths = resolved_compatibility_paths(repo_root, state_layout)
    return {
        "configuration": {
            "controller_defaults": {
                "path": str(paths.controller_defaults_path),
                "values": controller_defaults,
            },
            "adapter_settings": {
                "path": str(paths.adapter_settings_path),
                "values": adapter_settings,
                "summary": adapter_settings_summary(adapter_settings),
            },
            "routing_policy": {
                "path": str(routing_policy_path(paths.orchestration_dir)),
                "values": routing_policy,
            },
            "governance_policy": {
                "path": str(governance_policy_path(paths.orchestration_dir)),
                "values": governance_policy,
                "summary": {
                    "operating_profile": governance_policy.get("operating_profile"),
                    "active_snapshot": governance_snapshot,
                    "secret_scopes": resolve_secret_scopes(governance_policy),
                    "surface_version_pins": resolve_surface_version_pins(governance_policy),
                },
            },
            "state_layout": {
                "path": str(paths.state_layout_path),
                "values": state_layout,
            },
        },
        "workflow_defaults": routing_policy.get("workflow_defaults", {}),
        "state_paths": {
            "controller_lock": str(paths.controller_lock),
            "state_db": str(paths.state_db),
            "events_ndjson": str(paths.events_ndjson),
            "snapshots_dir": str(paths.snapshots_dir),
            "checkpoints_dir": str(paths.checkpoints_dir),
            "adapters_dir": str(paths.adapters_dir),
        },
        "compatibility_paths": {key: str(value) for key, value in compatibility_paths.items()},
        "compatibility": build_single_worker_compatibility_guidance(
            {key: str(value) for key, value in compatibility_paths.items()}
        ),
    }


def build_setup_dry_run(repo_root: Path, paths) -> dict[str, object]:
    missing = missing_setup_paths(paths)
    compatibility_paths = {
        "tmux_session_file": str(repo_root / ".codex" / "tmux-session.txt"),
        "tmux_socket_file": str(repo_root / ".codex" / "tmux-socket.txt"),
        "target_pane_file": str(repo_root / ".codex" / "target-pane.txt"),
        "legacy_target_pane_file": str(repo_root / "tools" / "tmux_bridge" / "target_pane.txt"),
    }
    reference_examples = {
        "bootstrap": [
            "macs setup init",
            "macs setup check --json",
        ],
        "registration": [
            "macs worker discover --json",
            "macs worker register --worker <worker-id> --adapter <adapter-id> --json",
        ],
        "routing": [
            "macs setup check --json",
        ],
        "validation": [
            "macs setup validate --json",
        ],
        "intervention": [
            "macs task pause --task <task-id> --confirm",
            "macs task resume --task <task-id> --confirm",
        ],
        "recovery": [
            "macs recovery inspect --task <task-id>",
            "macs recovery retry --task <task-id> --confirm",
            "macs recovery reconcile --task <task-id> --confirm",
        ],
    }
    steps = [
        {
            "step": 1,
            "command": "macs setup init",
            "purpose": "bootstrap repo-local orchestration state, config domains, and controller-owned policy files",
            "read_only": False,
        },
        {
            "step": 2,
            "command": "macs setup check --json",
            "purpose": "inspect repo-local config domains, compatibility paths, and routing-default visibility",
            "read_only": True,
        },
        {
            "step": 3,
            "command": "macs worker discover --json",
            "purpose": "discover tmux-backed workers on the local host without registering them",
            "read_only": False,
        },
        {
            "step": 4,
            "command": "macs worker register --worker <worker-id> --adapter <adapter-id> --json",
            "purpose": "register only the workers and adapters you want the controller to route against",
            "read_only": False,
        },
        {
            "step": 5,
            "command": "macs setup validate --json",
            "purpose": "check bootstrap, config visibility, local dependencies, adapter availability, worker readiness, and routing defaults",
            "read_only": True,
        },
        {
            "step": 6,
            "command": "macs task pause --task <task-id> --confirm",
            "purpose": "verify the operator-confirmed intervention path before relying on live work handoff controls",
            "read_only": False,
        },
        {
            "step": 7,
            "command": "macs recovery inspect --task <task-id>",
            "purpose": "verify the recovery path and the follow-up retry or reconcile commands for unresolved ownership",
            "read_only": True,
        },
    ]
    return {
        "read_only": True,
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "bootstrap_detected": not missing,
        "missing_paths": missing,
        "steps": steps,
        "reference_examples": reference_examples,
        "notes": [
            "Dry-run guidance is conservative and does not auto-install runtimes or auto-register workers.",
            "Runtime presence on PATH is only an availability hint; controller facts remain authoritative for readiness.",
        ],
        "next_action": "macs setup init" if missing else "macs setup validate --json",
        "migration_guidance": build_single_worker_compatibility_guidance(compatibility_paths),
    }


def build_setup_validation(repo_root: Path, paths) -> dict[str, object]:
    snapshot = build_setup_configuration_snapshot(repo_root, paths)
    adapter_settings = load_adapter_settings(paths.adapter_settings_path)
    workers = list_workers(paths.state_db)
    worker_states = _worker_state_counts(workers)
    ready_workers = worker_states.get("ready", 0)
    enabled_adapters = snapshot["configuration"]["adapter_settings"]["summary"]["enabled_adapters"]
    disabled_adapters = snapshot["configuration"]["adapter_settings"]["summary"]["disabled_adapters"]

    dependency_checks = []
    blocking_gaps = []
    for command, purpose in CORE_DEPENDENCIES:
        available = shutil.which(command) is not None
        dependency_checks.append(
            {
                "name": command,
                "purpose": purpose,
                "available": available,
            }
        )
        if not available:
            blocking_gaps.append(f"required dependency '{command}' is not available on PATH")

    if not enabled_adapters:
        blocking_gaps.append("no adapters are enabled in repo-local adapter settings")

    workflow_defaults = snapshot["workflow_defaults"]
    routing_defaults_visible = bool(workflow_defaults)
    if not routing_defaults_visible:
        blocking_gaps.append("routing defaults are not visible in routing-policy.json")

    adapter_checks = []
    readiness_gaps = []
    worker_summary_by_adapter = {}
    for descriptor in sorted(list_adapters(), key=lambda item: str(item["adapter_id"])):
        adapter_id = str(descriptor["adapter_id"])
        settings = adapter_configuration(adapter_settings, adapter_id)
        enabled = bool(settings.get("enabled", True))
        runtime_command = RUNTIME_BINARY_COMMANDS.get(adapter_id, adapter_id)
        runtime_available = True if runtime_command is None else shutil.which(runtime_command) is not None
        adapter_workers = [worker for worker in workers if worker["adapter_id"] == adapter_id]
        adapter_ready_workers = [worker for worker in adapter_workers if worker["state"] == "ready"]
        adapter_degraded_workers = [worker for worker in adapter_workers if worker["state"] == "degraded"]
        worker_summary_by_adapter[adapter_id] = {
            "total": len(adapter_workers),
            "ready": len(adapter_ready_workers),
            "degraded": len(adapter_degraded_workers),
        }
        adapter_checks.append(
            {
                **descriptor,
                "settings": settings,
                "enabled": enabled,
                "runtime_command": runtime_command,
                "runtime_available": runtime_available,
                "worker_summary": worker_summary_by_adapter[adapter_id],
            }
        )
        if not enabled:
            continue
        if runtime_command and not runtime_available:
            readiness_gaps.append(f"enabled adapter '{adapter_id}' runtime is not available on PATH")
        if not adapter_workers:
            readiness_gaps.append(f"enabled adapter '{adapter_id}' has no registered workers")
        elif not adapter_ready_workers:
            if adapter_degraded_workers:
                readiness_gaps.append(
                    f"enabled adapter '{adapter_id}' has no ready workers; only degraded workers are registered"
                )
            else:
                readiness_gaps.append(f"enabled adapter '{adapter_id}' has no ready workers")

    if ready_workers == 0:
        readiness_gaps.append("no ready workers are currently registered")

    safe_ready_state_reached = not blocking_gaps and not readiness_gaps
    if safe_ready_state_reached:
        outcome = "PASS"
    elif blocking_gaps:
        outcome = "FAIL"
    else:
        outcome = "PARTIAL"

    next_actions = []
    if blocking_gaps:
        next_actions.append("Install the missing controller dependencies and rerun `macs setup validate --json`.")
    runtime_gap_adapters = [
        item["adapter_id"]
        for item in adapter_checks
        if item["enabled"] and item["runtime_command"] and not item["runtime_available"]
    ]
    if runtime_gap_adapters:
        joined = ", ".join(runtime_gap_adapters)
        next_actions.append(
            f"Install or expose the enabled runtime binaries on PATH for: {joined}, or disable unused adapters in repo-local settings."
        )
    if readiness_gaps:
        next_actions.append(
            "Discover and register ready workers for the enabled adapters, then rerun `macs setup validate --json`."
        )
    if safe_ready_state_reached:
        next_actions.append("Proceed with normal task creation and assignment; intervention and recovery commands remain available.")

    checks = [
        {
            "name": "repo_local_bootstrap",
            "outcome": "PASS",
            "details": "repo-local orchestration bootstrap files are present",
        },
        {
            "name": "config_domains_visible",
            "outcome": "PASS",
            "details": "controller defaults, adapter settings, routing policy, governance policy, and state layout are visible",
        },
        {
            "name": "local_dependencies_ready",
            "outcome": "PASS" if not blocking_gaps else "FAIL",
            "details": dependency_checks,
        },
        {
            "name": "enabled_adapter_availability",
            "outcome": "PASS" if not runtime_gap_adapters else "PARTIAL",
            "details": adapter_checks,
        },
        {
            "name": "worker_readiness",
            "outcome": "PASS" if ready_workers > 0 and not readiness_gaps else "PARTIAL",
            "details": {
                "total": len(workers),
                "ready": ready_workers,
                "by_state": worker_states,
                "by_adapter": worker_summary_by_adapter,
            },
        },
        {
            "name": "routing_defaults_visible",
            "outcome": "PASS" if routing_defaults_visible else "FAIL",
            "details": sorted(workflow_defaults),
        },
    ]

    validation = {
        "outcome": outcome,
        "safe_ready_state_reached": safe_ready_state_reached,
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "config_domains_visible": True,
        "routing_defaults_visible": routing_defaults_visible,
        "workflow_defaults": sorted(workflow_defaults),
        "adapter_summary": {
            "enabled_adapters": enabled_adapters,
            "disabled_adapters": disabled_adapters,
            "adapters": adapter_checks,
        },
        "worker_summary": {
            "total": len(workers),
            "registered": len(workers),
            "ready": ready_workers,
            "by_state": worker_states,
            "by_adapter": worker_summary_by_adapter,
        },
        "dependency_summary": {
            "required_dependencies": dependency_checks,
        },
        "controller_facts": {
            "state_store_initialized": True,
            "worker_records_present": bool(workers),
            "routing_defaults_visible": routing_defaults_visible,
            "repo_local_configuration_domains_visible": True,
        },
        "gaps": [*blocking_gaps, *readiness_gaps],
        "next_actions": next_actions,
        "reference_examples": {
            "registration": [
                "macs worker discover --json",
                "macs worker register --worker <worker-id> --adapter <adapter-id> --json",
            ],
            "routing": [
                "macs setup check --json",
            ],
            "validation": [
                "macs setup validate --json",
            ],
            "intervention": [
                "macs task pause --task <task-id> --confirm",
            ],
            "recovery": [
                "macs recovery inspect --task <task-id>",
            ],
        },
        "evidence_fields": {
            "run_metadata": {
                "report_date": utc_now(),
                "repository": str(repo_root),
                "host_os": platform.platform(),
                "validation_scope": enabled_adapters,
                "outcome": outcome,
            },
            "preconditions": {
                "repo_local_state_path": str(paths.orchestration_dir),
                "required_local_dependencies_present": not blocking_gaps,
                "known_deviations": [],
            },
            "story_checks": {
                "supported_runtimes_can_be_registered": bool(enabled_adapters),
                "worker_readiness_can_be_validated_end_to_end": True,
                "routing_defaults_can_be_inspected": routing_defaults_visible,
                "reference_examples_exist_for_registration": True,
                "reference_examples_exist_for_intervention": True,
                "reference_examples_exist_for_recovery": True,
            },
            "artifacts": {
                "config_files": [
                    snapshot["configuration"]["controller_defaults"]["path"],
                    snapshot["configuration"]["adapter_settings"]["path"],
                    snapshot["configuration"]["routing_policy"]["path"],
                    snapshot["configuration"]["governance_policy"]["path"],
                    snapshot["configuration"]["state_layout"]["path"],
                ],
                "state_paths": snapshot["state_paths"],
                "compatibility_paths": snapshot["compatibility_paths"],
            },
        },
    }
    return {
        "status": validation,
        "validation": validation,
        "checks": checks,
    }


def build_setup_guide(repo_root: Path, paths) -> dict[str, object]:
    dry_run = build_setup_dry_run(repo_root, paths)
    bootstrap_detected = bool(dry_run["bootstrap_detected"])
    validation = build_setup_validation(repo_root, paths)["validation"] if bootstrap_detected else None
    phase = _guide_phase(bootstrap_detected, validation)
    next_action, follow_up_commands = _guide_commands_for_guide_state(phase, dry_run, validation)
    current_state = {
        "bootstrap_detected": bootstrap_detected,
        "outcome": validation["outcome"] if validation else None,
        "safe_ready_state": bool(validation["safe_ready_state_reached"]) if validation else False,
        "enabled_adapters": validation["adapter_summary"]["enabled_adapters"] if validation else [],
        "registered_workers": validation["worker_summary"]["registered"] if validation else 0,
        "ready_workers": validation["worker_summary"]["ready"] if validation else 0,
    }
    return {
        "command": "macs setup guide",
        "read_only": True,
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "bootstrap_detected": bootstrap_detected,
        "current_phase": phase,
        "orientation": dict(GUIDE_ORIENTATION),
        "current_state": current_state,
        "next_action": next_action,
        "follow_up_commands": follow_up_commands,
    }


def _guide_commands_for_guide_state(
    phase: str,
    dry_run: dict[str, object],
    validation: dict[str, object] | None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if validation is not None:
        worker_summary = validation["worker_summary"]
        if validation["safe_ready_state_reached"]:
            return (
                _guide_command(dry_run, "macs setup validate --json"),
                [
                    _guide_command(dry_run, "macs setup check --json"),
                ],
            )
        if worker_summary["registered"] == 0:
            return (
                _guide_command(dry_run, "macs worker discover --json"),
                [
                    _guide_command(dry_run, "macs setup check --json"),
                    _guide_command(dry_run, "macs setup validate --json"),
                ],
            )
        if worker_summary["ready"] == 0:
            return (
                _guide_command(
                    dry_run,
                    "macs worker discover --json",
                    purpose_override=(
                        "refresh controller worker evidence and discover any additional workers before rerunning readiness validation"
                    ),
                ),
                [
                    _guide_command(dry_run, "macs setup validate --json"),
                ],
            )
    return _guide_commands_for_phase(phase, dry_run)


def _guide_phase(bootstrap_detected: bool, validation: dict[str, object] | None) -> str:
    if not bootstrap_detected:
        return "bootstrap-required"
    if validation is None:
        return "inspect-configuration"
    if validation["safe_ready_state_reached"]:
        return "ready"
    if validation["worker_summary"]["registered"] == 0:
        return "register-workers"
    if validation["worker_summary"]["ready"] == 0:
        return "validate-readiness"
    return "inspect-configuration"


def _guide_commands_for_phase(
    phase: str,
    dry_run: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if phase == "bootstrap-required":
        return (
            _guide_command(dry_run, "macs setup init"),
            [
                _guide_command(
                    dry_run,
                    "macs setup dry-run --json",
                    purpose_override="inspect the conservative onboarding path without mutating controller state",
                )
            ],
        )
    if phase == "register-workers":
        return (
            _guide_command(dry_run, "macs worker discover --json"),
            [
                _guide_command(dry_run, "macs setup check --json"),
                _guide_command(dry_run, "macs setup validate --json"),
            ],
        )
    if phase == "validate-readiness":
        return (
            _guide_command(dry_run, "macs setup validate --json"),
            [
                _guide_command(dry_run, "macs worker discover --json"),
            ],
        )
    if phase == "ready":
        return (
            _guide_command(dry_run, "macs setup validate --json"),
            [
                _guide_command(dry_run, "macs setup check --json"),
            ],
        )
    return (
        _guide_command(dry_run, "macs setup check --json"),
        [
            _guide_command(dry_run, "macs setup validate --json"),
        ],
    )


def _guide_command(
    dry_run: dict[str, object],
    command: str,
    *,
    purpose_override: str | None = None,
) -> dict[str, object]:
    step = _dry_run_step(dry_run, command)
    read_only = bool(step["read_only"]) if step else command.startswith("macs setup ")
    purpose = purpose_override or (str(step["purpose"]) if step else "follow the controller-owned onboarding path")
    return {
        "command": command,
        "purpose": purpose,
        "read_only": read_only,
        "action_type": "READ-ONLY" if read_only else "ACTION",
    }


def _dry_run_step(dry_run: dict[str, object], command: str) -> dict[str, object] | None:
    for step in dry_run.get("steps", []):
        if step.get("command") == command:
            return step
    return None


def _worker_state_counts(workers: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for worker in workers:
        state = str(worker["state"])
        counts[state] = counts.get(state, 0) + 1
    return counts


def build_single_worker_compatibility_guidance(compatibility_paths: dict[str, str]) -> dict[str, object]:
    return {
        "state_migration_required": False,
        "migration_summary": "No repo-local state migration is required.",
        "single_worker_mode_supported": True,
        "single_worker_mode_summary": (
            "Single-worker mode remains a supported one-worker specialization of the controller-owned control-plane model."
        ),
        "legacy_metadata": {
            "tmux_session_file": compatibility_paths["tmux_session_file"],
            "tmux_socket_file": compatibility_paths["tmux_socket_file"],
            "target_pane_file": compatibility_paths["target_pane_file"],
            "legacy_target_pane_file": compatibility_paths["legacy_target_pane_file"],
        },
        "supported_unchanged_workflows": {
            "bridge_helpers": [
                "./tools/tmux_bridge/snapshot.sh",
                "./tools/tmux_bridge/send.sh \"<instruction>\"",
                "./tools/tmux_bridge/status.sh",
                "./tools/tmux_bridge/set_target.sh --pane %X",
            ],
            "launchers": [
                "../macs/start-worker.sh macs",
                "../macs/start-controller.sh",
            ],
        },
        "superseded_by_control_plane": {
            "normal_orchestration": [
                "macs task create --summary <text>",
                "macs task assign --task <task-id> --worker <worker-id>",
                "macs task inspect --task <task-id>",
                "macs worker inspect --worker <worker-id> --open-pane",
            ],
            "intervention_and_recovery": [
                "macs task pause --task <task-id> --confirm",
                "macs recovery inspect --task <task-id>",
            ],
        },
    }
