#!/usr/bin/env python3
"""MACS orchestration CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.orchestration.session import (
    ControllerSessionLock,
    SessionLockHeldError,
    build_paths,
    build_lock_metadata,
    ensure_orchestration_store,
    render_lock_error,
    setup_orchestration,
)
from tools.orchestration.adapters.registry import get_adapter, list_adapters
from tools.orchestration.cli.rendering import key_value_lines, terminal_render_context
from tools.orchestration.config import (
    adapter_configuration,
    adapter_enabled,
    adapter_settings_summary,
    load_adapter_settings,
    load_controller_defaults,
    load_state_layout,
    resolved_compatibility_paths,
)
from tools.orchestration.history import (
    checkpoint_for_ref,
    decision_event_for_ref,
    ObjectNotFoundError,
    inspect_event,
    inspect_lease,
    list_aggregate_events,
    list_events,
    list_lease_history,
    summarize_governance_evidence,
)
from tools.orchestration.health import classify_workers
from tools.orchestration.invariants import InvariantViolationError
from tools.orchestration.interventions import (
    build_runtime_pause_resume_status,
    intervention_blocking_condition,
    intervention_next_action,
    runtime_intervention_warnings,
)
from tools.orchestration.locks import LockConflictError, inspect_lock, list_locks
from tools.orchestration.overview import build_overview
from tools.orchestration.policy import (
    SURFACE_VERSION_PIN_SELECTOR_ANY,
    active_governance_snapshot,
    describe_adapter_governance,
    evaluate_decision_rights,
    evaluate_worker_governance,
    governance_policy_path,
    load_governance_policy,
    load_routing_policy,
    routing_policy_path,
)
from tools.orchestration.release_gate import run_release_gate
from tools.orchestration.recovery import inspect_recovery_context
from tools.orchestration.setup import (
    build_setup_configuration_snapshot,
    build_setup_dry_run,
    build_setup_guide,
    build_setup_validation,
    missing_setup_paths,
)
from tools.orchestration.store import connect_state_db
from tools.orchestration.workers import (
    WorkerNotFoundError,
    discover_tmux_workers,
    inspect_worker,
    inspect_worker_context,
    list_workers,
    register_worker,
    set_worker_state,
    sync_discovered_workers,
)
from tools.orchestration.routing import RoutingError
from tools.orchestration.tasks import (
    archive_task,
    checkpoint_task,
    reconcile_task_recovery,
    freeze_owned_active_tasks_for_worker,
    pause_task,
    resume_task,
    reroute_task,
    retry_task_recovery,
    TaskActionError,
    TaskNotFoundError,
    assign_task,
    close_task,
    create_task_record,
    inspect_task,
    inspect_task_context,
    list_tasks,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="macs", description="MACS orchestration CLI")
    parser.add_argument(
        "--repo",
        default=os.getcwd(),
        help="repo root to operate against (default: current working directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable output",
    )

    subparsers = parser.add_subparsers(dest="family", required=True)
    setup_parser = subparsers.add_parser("setup", help="onboarding and bootstrap commands")
    setup_subparsers = setup_parser.add_subparsers(dest="verb", required=True)
    worker_parser = subparsers.add_parser("worker", help="worker discovery and governance commands")
    worker_subparsers = worker_parser.add_subparsers(dest="verb", required=True)
    adapter_parser = subparsers.add_parser("adapter", help="adapter contract inspection commands")
    adapter_subparsers = adapter_parser.add_subparsers(dest="verb", required=True)
    task_parser = subparsers.add_parser("task", help="task creation and assignment commands")
    task_subparsers = task_parser.add_subparsers(dest="verb", required=True)
    lock_parser = subparsers.add_parser("lock", help="lock inspection commands")
    lock_subparsers = lock_parser.add_subparsers(dest="verb", required=True)
    lease_parser = subparsers.add_parser("lease", help="lease inspection commands")
    lease_subparsers = lease_parser.add_subparsers(dest="verb", required=True)
    event_parser = subparsers.add_parser("event", help="event inspection commands")
    event_subparsers = event_parser.add_subparsers(dest="verb", required=True)
    overview_parser = subparsers.add_parser("overview", help="overview summary commands")
    overview_subparsers = overview_parser.add_subparsers(dest="verb", required=True)
    recovery_parser = subparsers.add_parser("recovery", help="recovery and reconciliation commands")
    recovery_subparsers = recovery_parser.add_subparsers(dest="verb", required=True)

    init_parser = setup_subparsers.add_parser(
        "init", help="create the orchestration layout and optionally hold the controller lock"
    )
    init_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=argparse.SUPPRESS,
    )
    init_parser.add_argument(
        "--exec",
        dest="exec_cmd",
        nargs=argparse.REMAINDER,
        help="command to exec while holding the controller lock",
    )

    check_parser = setup_subparsers.add_parser("check", help="inspect repo-local setup and configuration domains")
    check_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=argparse.SUPPRESS,
    )
    validate_parser = setup_subparsers.add_parser(
        "validate",
        help="validate repo-local adoption readiness without mutating controller state",
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=argparse.SUPPRESS,
    )
    validate_parser.add_argument(
        "--release-gate",
        action="store_true",
        help="run the Phase 1 release gate and write the release-evidence package",
    )
    dry_run_parser = setup_subparsers.add_parser("dry-run", help="show a conservative read-only onboarding path")
    dry_run_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=argparse.SUPPRESS,
    )
    guide_parser = setup_subparsers.add_parser("guide", help="show a read-only guided onboarding briefing")
    guide_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help=argparse.SUPPRESS,
    )

    worker_list_parser = worker_subparsers.add_parser("list", help="list known workers")
    worker_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)

    worker_discover_parser = worker_subparsers.add_parser(
        "discover", help="discover tmux-backed workers and refresh the roster"
    )
    worker_discover_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    worker_discover_parser.add_argument("--tmux-socket", dest="tmux_socket", help="tmux socket override")
    worker_discover_parser.add_argument("--tmux-session", dest="tmux_session", help="tmux session override")

    worker_inspect_parser = worker_subparsers.add_parser("inspect", help="inspect one worker")
    worker_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    worker_inspect_parser.add_argument("--worker", required=True, dest="worker_id", help="worker id")
    worker_inspect_parser.add_argument("--open-pane", action="store_true", dest="open_pane", help="pin and open pane")

    worker_register_parser = worker_subparsers.add_parser("register", help="register a discovered worker")
    worker_register_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    worker_register_parser.add_argument("--worker", required=True, dest="worker_id", help="worker id")
    worker_register_parser.add_argument("--adapter", required=True, dest="adapter_id", help="adapter id")

    for verb in ("enable", "disable", "quarantine"):
        worker_state_parser = worker_subparsers.add_parser(verb, help=f"{verb} a worker")
        worker_state_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
        worker_state_parser.add_argument("--worker", required=True, dest="worker_id", help="worker id")

    adapter_list_parser = adapter_subparsers.add_parser("list", help="list adapters")
    adapter_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)

    adapter_inspect_parser = adapter_subparsers.add_parser("inspect", help="inspect one adapter")
    adapter_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    adapter_inspect_parser.add_argument("--adapter", required=True, dest="adapter_id", help="adapter id")

    adapter_probe_parser = adapter_subparsers.add_parser("probe", help="probe adapter evidence")
    adapter_probe_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    adapter_probe_group = adapter_probe_parser.add_mutually_exclusive_group(required=True)
    adapter_probe_group.add_argument("--adapter", dest="adapter_id", help="adapter id")
    adapter_probe_group.add_argument("--worker", dest="worker_id", help="worker id")

    adapter_validate_parser = adapter_subparsers.add_parser("validate", help="validate adapter contract shape")
    adapter_validate_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    adapter_validate_parser.add_argument("--adapter", required=True, dest="adapter_id", help="adapter id")

    task_list_parser = task_subparsers.add_parser("list", help="list tasks")
    task_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)

    task_create_parser = task_subparsers.add_parser("create", help="create a task")
    task_create_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_create_parser.add_argument("--summary", required=True, dest="summary", help="task summary")
    task_create_parser.add_argument(
        "--workflow-class",
        dest="workflow_class",
        help="workflow class (default: controller config)",
    )
    task_create_parser.add_argument(
        "--require-capability", action="append", dest="required_capabilities", default=[], help="required capability"
    )
    task_create_parser.add_argument(
        "--surface", action="append", dest="protected_surfaces", default=[], help="protected surface"
    )

    task_assign_parser = task_subparsers.add_parser("assign", help="assign a task")
    task_assign_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_assign_parser.add_argument("--task", required=True, dest="task_id", help="task id")
    task_assign_group = task_assign_parser.add_mutually_exclusive_group(required=False)
    task_assign_group.add_argument("--worker", dest="worker_id", help="worker id")
    task_assign_group.add_argument("--workflow-class", dest="workflow_class", help="workflow class selector")

    task_inspect_parser = task_subparsers.add_parser("inspect", help="inspect a task")
    task_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_inspect_parser.add_argument("--task", required=True, dest="task_id", help="task id")
    task_inspect_parser.add_argument("--open-pane", action="store_true", dest="open_pane", help="pin and open pane")

    task_checkpoint_parser = task_subparsers.add_parser(
        "checkpoint",
        help="capture repo-native diff/review evidence for a task-scoped guarded action",
    )
    task_checkpoint_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_checkpoint_parser.add_argument("--task", required=True, dest="task_id", help="task id")
    task_checkpoint_parser.add_argument(
        "--target-action",
        required=True,
        dest="target_action",
        help="supported checkpoint target action, for example task.close or task.archive",
    )

    for verb in ("close", "archive", "pause", "resume", "abort"):
        task_action_parser = task_subparsers.add_parser(verb, help=f"{verb} a task")
        task_action_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
        task_action_parser.add_argument("--task", required=True, dest="task_id", help="task id")
        if verb in {"pause", "resume", "abort"}:
            task_action_parser.add_argument(
                "--confirm",
                action="store_true",
                dest="confirm",
                help="explicit operator confirmation",
            )
        if verb == "pause":
            task_action_parser.add_argument(
                "--rationale",
                dest="rationale",
                help="operator rationale for the intervention decision",
            )

    task_reroute_parser = task_subparsers.add_parser("reroute", help="reroute a task")
    task_reroute_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_reroute_parser.add_argument("--task", required=True, dest="task_id", help="task id")
    task_reroute_parser.add_argument(
        "--rationale",
        dest="rationale",
        help="operator rationale for the intervention decision",
    )
    task_reroute_parser.add_argument(
        "--confirm",
        action="store_true",
        dest="confirm",
        help="explicit operator confirmation",
    )
    task_reroute_group = task_reroute_parser.add_mutually_exclusive_group(required=True)
    task_reroute_group.add_argument("--worker", dest="worker_id", help="worker id")
    task_reroute_group.add_argument("--workflow-class", dest="workflow_class", help="workflow class selector")

    lock_list_parser = lock_subparsers.add_parser("list", help="list locks")
    lock_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    lock_inspect_parser = lock_subparsers.add_parser("inspect", help="inspect one lock")
    lock_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    lock_inspect_parser.add_argument("--lock", required=True, dest="lock_id", help="lock id")
    for verb in ("override", "release"):
        lock_action_parser = lock_subparsers.add_parser(verb, help=f"{verb} a lock")
        lock_action_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
        lock_action_parser.add_argument("--lock", required=True, dest="lock_id", help="lock id")
        lock_action_parser.add_argument(
            "--confirm",
            action="store_true",
            dest="confirm",
            help="explicit operator confirmation",
        )

    lease_inspect_parser = lease_subparsers.add_parser("inspect", help="inspect a lease")
    lease_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    lease_inspect_parser.add_argument("--lease", required=True, dest="lease_id", help="lease id")

    lease_history_parser = lease_subparsers.add_parser("history", help="show lease history")
    lease_history_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    lease_history_group = lease_history_parser.add_mutually_exclusive_group(required=True)
    lease_history_group.add_argument("--task", dest="task_id", help="task id")
    lease_history_group.add_argument("--worker", dest="worker_id", help="worker id")

    event_list_parser = event_subparsers.add_parser("list", help="list events")
    event_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)

    event_inspect_parser = event_subparsers.add_parser("inspect", help="inspect one event")
    event_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    event_inspect_parser.add_argument("--event", required=True, dest="event_id", help="event id")

    overview_show_parser = overview_subparsers.add_parser("show", help="show orchestration overview")
    overview_show_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    recovery_inspect_parser = recovery_subparsers.add_parser("inspect", help="inspect recovery context")
    recovery_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    recovery_inspect_parser.add_argument("--task", required=True, dest="task_id", help="task id")
    for verb in ("reconcile", "retry"):
        recovery_action_parser = recovery_subparsers.add_parser(verb, help=f"{verb} recovery context")
        recovery_action_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
        recovery_action_parser.add_argument("--task", required=True, dest="task_id", help="task id")
        recovery_action_parser.add_argument(
            "--confirm",
            action="store_true",
            dest="confirm",
            help="explicit operator confirmation",
        )
        recovery_action_parser.add_argument(
            "--rationale",
            dest="rationale",
            help="operator rationale for the intervention decision",
        )
    return parser.parse_args()


def emit_setup_result(
    args: argparse.Namespace,
    ok: bool,
    command_name: str,
    data: dict[str, object],
    exit_code: int,
) -> int:
    if args.json_output:
        payload = {
            "ok": ok,
            "command": command_name,
            "data": data if ok else {},
            "error": None if ok else data,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if ok:
            if command_name == "macs setup init":
                print("Initialized repo-local orchestration layout.")
                print(f"Orchestration dir: {data['orchestration_dir']}")
                print(f"Controller lock: {data['controller_lock']}")
                print(f"State DB ({data['state_db_status']}): {data['state_db']}")
                print(f"Events export ({data['events_ndjson_status']}): {data['events_ndjson']}")
                print(
                    f"Controller defaults ({data['controller_defaults']['status']}): "
                    f"{data['controller_defaults']['path']}"
                )
                print(
                    f"Adapter settings ({data['adapter_settings']['status']}): "
                    f"{data['adapter_settings']['path']}"
                )
                print(
                    f"Routing policy ({data['routing_policy']['status']}): {data['routing_policy']['path']}"
                )
                print(
                    f"Governance policy ({data['governance_policy']['status']}): "
                    f"{data['governance_policy']['path']}"
                )
                print(
                    f"State layout ({data['state_layout']['status']}): "
                    f"{data['state_layout']['path']}"
                )
                print(
                    "Startup summary: "
                    f"{data['startup_summary']['restored_entities']['tasks']} tasks restored, "
                    f"{len(data['startup_summary']['unresolved_anomalies']['tasks_pending_reconciliation'])} pending reconciliation, "
                    f"assignments blocked={data['startup_summary']['assignments_blocked']}"
                )
                pending_recovery_runs = data["startup_summary"].get("pending_recovery_runs", [])
                if pending_recovery_runs:
                    print(f"Pending recovery runs: {len(pending_recovery_runs)}")
                    for run in pending_recovery_runs:
                        task_id = run.get("task_id") or "controller"
                        print(f"{run['recovery_run_id']}  {run['state']}  task={task_id}")
                if data.get("holding_lock"):
                    print("Controller session lock acquired.")
            elif command_name == "macs setup check":
                emit_setup_check_human_readable(data)
            elif command_name == "macs setup validate":
                emit_setup_validate_human_readable(data)
            elif command_name == "macs setup dry-run":
                emit_setup_dry_run_human_readable(data)
            elif command_name == "macs setup guide":
                emit_setup_guide_human_readable(data)
        else:
            if command_name == "macs setup validate" and data.get("outcome"):
                print(f"Outcome: {data['outcome']}", file=sys.stderr)
                print(data["message"], file=sys.stderr)
                if data.get("next_action"):
                    print(f"Next Action: {data['next_action']}", file=sys.stderr)
            else:
                print(data["message"], file=sys.stderr)
                if data.get("next_action"):
                    print(f"Next Action: {data['next_action']}", file=sys.stderr)
    return exit_code


def emit_result(args: argparse.Namespace, ok: bool, data: dict[str, object], exit_code: int) -> int:
    return emit_setup_result(args, ok, f"macs {args.family} {args.verb}", data, exit_code)


def emit_setup_check_human_readable(data: dict[str, object]) -> None:
    print("Configuration domains:")
    configuration = data["configuration"]
    print(f"Controller defaults: {configuration['controller_defaults']['path']}")
    print(
        "Default workflow class: "
        f"{configuration['controller_defaults']['values']['task']['default_workflow_class']}"
    )
    print(f"Adapter settings: {configuration['adapter_settings']['path']}")
    summary = configuration["adapter_settings"].get("summary", {})
    enabled = summary.get("enabled_adapters") or []
    disabled = summary.get("disabled_adapters") or []
    print(f"Enabled adapters: {', '.join(enabled) if enabled else 'none'}")
    print(f"Disabled adapters: {', '.join(disabled) if disabled else 'none'}")
    print(f"Routing policy: {configuration['routing_policy']['path']}")
    print(
        "Workflow classes: "
        f"{', '.join(sorted(data['workflow_defaults'])) if data['workflow_defaults'] else 'none'}"
    )
    print(f"Governance policy: {configuration['governance_policy']['path']}")
    governance_summary = configuration["governance_policy"].get("summary", {})
    if isinstance(governance_summary, dict):
        print(f"Active operating profile: {governance_summary.get('operating_profile', 'unknown')}")
        snapshot = governance_summary.get("active_snapshot") or {}
        print(f"Governance snapshot: {format_governance_snapshot_reference(snapshot)}")
        if snapshot.get("traceability_status") == "stale_vs_live_policy":
            for line in surface_version_pin_summary_lines(
                snapshot.get("surface_version_pins"),
                label="Snapshot-captured surface version pins",
            ):
                print(line)
            for line in secret_scope_summary_lines(
                snapshot.get("secret_scopes"),
                label="Snapshot-captured secret scopes",
            ):
                print(line)
        for line in surface_version_pin_summary_lines(governance_summary.get("surface_version_pins")):
            print(line)
        for line in secret_scope_summary_lines(governance_summary.get("secret_scopes")):
            print(line)
    print(f"State layout: {configuration['state_layout']['path']}")
    print("State paths:")
    for key, value in data["state_paths"].items():
        print(f"- {key}: {value}")
    print("Compatibility paths:")
    for key, value in data["compatibility_paths"].items():
        print(f"- {key}: {value}")
    compatibility = data.get("compatibility")
    if isinstance(compatibility, dict):
        print("Single-worker compatibility:")
        print(f"State migration required: {'yes' if compatibility['state_migration_required'] else 'no'}")
        print(f"Single-worker mode: {'supported' if compatibility['single_worker_mode_supported'] else 'unsupported'}")
        print(f"Migration summary: {compatibility['migration_summary']}")
        print("Legacy metadata:")
        for key, value in compatibility["legacy_metadata"].items():
            print(f"- {key}: {value}")
        print("Supported unchanged helpers:")
        for key, commands in compatibility["supported_unchanged_workflows"].items():
            print(f"- {key}: {', '.join(commands)}")
        print("Superseded by controller-owned commands:")
        for key, commands in compatibility["superseded_by_control_plane"].items():
            print(f"- {key}: {', '.join(commands)}")


def emit_setup_validate_human_readable(data: dict[str, object]) -> None:
    release_gate = data.get("release_gate")
    if isinstance(release_gate, dict):
        print(f"Release Gate Outcome: {release_gate['outcome']}")
        print(f"Invocation: {release_gate['invocation']}")
        print("Criteria:")
        for criterion, summary in release_gate["criteria"].items():
            print(f"- {criterion}: {summary['outcome']}")
            if criterion == "adapter_qualification":
                for adapter in summary.get("adapters", []):
                    print(f"  - {adapter['adapter_id']}: {adapter['outcome']}")
            if criterion == "failure_mode_matrix":
                for failure_class in summary.get("failure_classes", []):
                    print(f"  - {failure_class['failure_class']}: {failure_class['outcome']}")
            if criterion == "governance_hardening":
                for control in summary.get("controls", []):
                    evidence_ref = control.get("evidence_ref") or "none"
                    print(f"  - {control['control_id']}: {control['outcome']} (evidence: {evidence_ref})")
        print("Evidence:")
        print(f"- setup_validation_report: {release_gate['evidence']['setup_validation_report']}")
        for adapter_id, report_path in release_gate["evidence"]["adapter_reports"].items():
            print(f"- adapter_report[{adapter_id}]: {report_path}")
        print(f"- failure_mode_matrix_report: {release_gate['evidence']['failure_mode_matrix_report']}")
        print(f"- restart_recovery_report: {release_gate['evidence']['restart_recovery_report']}")
        print(f"- governance_hardening_report: {release_gate['evidence']['governance_hardening_report']}")
        print(f"- governance_hardening_summary_json: {release_gate['evidence']['governance_hardening_summary_json']}")
        print(f"- four_worker_dogfood_report: {release_gate['evidence']['four_worker_dogfood_report']}")
        print(f"- release_gate_report: {release_gate['evidence']['release_gate_report']}")
        print(f"- release_gate_summary_json: {release_gate['evidence']['release_gate_summary_json']}")
        next_actions = release_gate.get("next_actions", [])
        if next_actions:
            print("Next Actions:")
            for action in next_actions:
                print(f"- {action}")
        return

    validation = data["validation"]
    print(f"Outcome: {validation['outcome']}")
    print(f"Safe Ready State: {'yes' if validation['safe_ready_state_reached'] else 'no'}")
    print(f"Repo: {validation['repo_root']}")
    print(f"Orchestration dir: {validation['orchestration_dir']}")
    adapter_summary = validation["adapter_summary"]
    print(f"Enabled adapters: {', '.join(adapter_summary['enabled_adapters']) or 'none'}")
    print(f"Disabled adapters: {', '.join(adapter_summary['disabled_adapters']) or 'none'}")
    print(
        "Workers: "
        f"registered={validation['worker_summary']['registered']} "
        f"ready={validation['worker_summary']['ready']}"
    )
    print(f"Routing defaults visible: {'yes' if validation['routing_defaults_visible'] else 'no'}")
    print("Dependencies:")
    for item in validation["dependency_summary"]["required_dependencies"]:
        print(f"- {item['name']}: {'available' if item['available'] else 'missing'}")
    print("Enabled adapter readiness:")
    for item in adapter_summary["adapters"]:
        if not item["enabled"]:
            continue
        runtime_status = "available"
        if item["runtime_command"] and not item["runtime_available"]:
            runtime_status = "missing"
        elif item["runtime_command"] is None:
            runtime_status = "not required"
        print(
            f"- {item['adapter_id']}: runtime={runtime_status} "
            f"registered={item['worker_summary']['total']} ready={item['worker_summary']['ready']}"
        )
    gaps = validation.get("gaps", [])
    if gaps:
        print("Gaps:")
        for gap in gaps:
            print(f"- {gap}")
    next_actions = validation.get("next_actions", [])
    if next_actions:
        print("Next Actions:")
        for action in next_actions:
            print(f"- {action}")


def emit_setup_dry_run_human_readable(data: dict[str, object]) -> None:
    dry_run = data["dry_run"]
    print("Conservative setup dry-run:")
    print(f"Read only: {'yes' if dry_run['read_only'] else 'no'}")
    print(f"Bootstrap detected: {'yes' if dry_run['bootstrap_detected'] else 'no'}")
    print("Steps:")
    for step in dry_run["steps"]:
        print(f"{step['step']}. {step['command']}")
        print(f"   {step['purpose']}")
    if dry_run["missing_paths"]:
        print("Missing bootstrap paths:")
        for path in dry_run["missing_paths"]:
            print(f"- {path}")
    print("Reference examples:")
    for category, commands in dry_run["reference_examples"].items():
        print(f"- {category}: {', '.join(commands)}")
    compatibility = dry_run.get("migration_guidance")
    if isinstance(compatibility, dict):
        print("Single-worker migration:")
        print(compatibility["migration_summary"])
        print(
            "Single-worker mode: "
            f"{'supported' if compatibility['single_worker_mode_supported'] else 'unsupported'}"
        )
        print("Legacy metadata:")
        for key, value in compatibility["legacy_metadata"].items():
            print(f"- {key}: {value}")
        print("Supported unchanged helpers:")
        for key, commands in compatibility["supported_unchanged_workflows"].items():
            print(f"- {key}: {', '.join(commands)}")
        print("Use controller-owned commands for normal orchestration:")
        for key, commands in compatibility["superseded_by_control_plane"].items():
            print(f"- {key}: {', '.join(commands)}")
    print(f"Next action: {dry_run['next_action']}")


def emit_setup_guide_human_readable(data: dict[str, object]) -> None:
    guide = data["guide"]
    current_state = guide.get("current_state") or {}
    orientation = guide.get("orientation") or {}
    print("Guided setup briefing:")
    print(orientation.get("summary", "Controller-owned setup guidance."))
    print(f"Authority: {orientation.get('authority_note', 'Controller facts determine readiness.')}")
    print(f"Repo: {guide['repo_root']}")
    print(f"Bootstrap detected: {'yes' if guide['bootstrap_detected'] else 'no'}")
    print(f"Current phase: {guide['current_phase']}")
    if current_state.get("outcome"):
        print(f"Outcome: {current_state['outcome']}")
        print(f"Safe ready state: {'yes' if current_state.get('safe_ready_state') else 'no'}")
    print("Next command:")
    emit_setup_guide_command(guide["next_action"])
    follow_up_commands = guide.get("follow_up_commands") or []
    if follow_up_commands:
        print("Follow-up commands:")
        for command in follow_up_commands:
            emit_setup_guide_command(command)


def emit_setup_guide_command(command: dict[str, object]) -> None:
    print(f"[{command['action_type']}] {command['command']}")
    print(f"  {command['purpose']}")


def action_result_with_decision_rights(
    result: dict[str, object] | None,
    decision_rights: dict[str, object] | None,
    *,
    controller_state_changed: bool | None = None,
    affected_refs: dict[str, object] | None = None,
    next_action: str | None = None,
) -> dict[str, object]:
    updated = dict(result or {})
    if decision_rights is not None:
        updated["decision_rights"] = decision_rights
    if controller_state_changed is not None and "controller_state_changed" not in updated:
        updated["controller_state_changed"] = controller_state_changed
    if affected_refs is not None and "affected_refs" not in updated:
        updated["affected_refs"] = affected_refs
    if next_action is not None and "next_action" not in updated:
        updated["next_action"] = next_action
    return updated


def decision_rights_confirmation_label(decision_rights: dict[str, object] | None) -> str | None:
    if not isinstance(decision_rights, dict):
        return None
    if decision_rights.get("confirmation_required"):
        return "confirmed" if decision_rights.get("operator_confirmation_received") else "required"
    return "not required"


def emit_action_error_human(message: str, result: dict[str, object]) -> None:
    render_context = terminal_render_context()
    print(message, file=sys.stderr)
    decision_rights = result.get("decision_rights")
    if isinstance(decision_rights, dict):
        for line in key_value_lines("Decision Rights", decision_rights["decision_class"], render_context):
            print(line, file=sys.stderr)
        confirmation = decision_rights_confirmation_label(decision_rights)
        if confirmation is not None:
            for line in key_value_lines("Confirmation", confirmation, render_context):
                print(line, file=sys.stderr)
    if "controller_state_changed" in result:
        for line in key_value_lines(
            "Controller State Changed",
            "yes" if result.get("controller_state_changed") else "no",
            render_context,
        ):
            print(line, file=sys.stderr)
    affected_refs = format_affected_refs(result.get("affected_refs"))
    if affected_refs:
        for line in key_value_lines("Affected Refs", affected_refs, render_context):
            print(line, file=sys.stderr)
    if result.get("next_action"):
        for line in key_value_lines("Next Action", result["next_action"], render_context):
            print(line, file=sys.stderr)
    review_gate = result.get("review_gate")
    if isinstance(review_gate, dict):
        gate_outcome = review_gate.get("gate_outcome") or review_gate.get("status")
        if gate_outcome:
            for line in key_value_lines("Gate Outcome", str(gate_outcome), render_context):
                print(line, file=sys.stderr)
        if review_gate.get("target_action"):
            for line in key_value_lines("Target Action", str(review_gate["target_action"]), render_context):
                print(line, file=sys.stderr)
        checkpoint = review_gate.get("checkpoint")
        if isinstance(checkpoint, dict) and checkpoint.get("checkpoint_id"):
            for line in key_value_lines("Checkpoint", str(checkpoint["checkpoint_id"]), render_context):
                print(line, file=sys.stderr)
        conflicting_checkpoint = review_gate.get("conflicting_checkpoint")
        if isinstance(conflicting_checkpoint, dict) and conflicting_checkpoint.get("checkpoint_id"):
            for line in key_value_lines("Conflicting Checkpoint", str(conflicting_checkpoint["checkpoint_id"]), render_context):
                print(line, file=sys.stderr)
        if review_gate.get("decision_event_id"):
            for line in key_value_lines("Decision Event", str(review_gate["decision_event_id"]), render_context):
                print(line, file=sys.stderr)
    for line in secret_resolution_lines(result.get("secret_resolution")):
        print(line, file=sys.stderr)
    for line in routing_rejection_lines(result.get("routing_evaluation")):
        print(line, file=sys.stderr)


def emit_task_action_result(args: argparse.Namespace, verb: str, action: dict[str, object]) -> int:
    event = action["event"]
    payload = {
        "ok": True,
        "command": f"macs task {verb}",
        "timestamp": event["timestamp"],
        "warnings": action.get("warnings", []),
        "errors": [],
        "data": {
            "result": action["result"],
            "event": event,
        },
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    result = action["result"]
    render_context = terminal_render_context()
    decision_rights = result.get("decision_rights")
    if verb == "create":
        task = result["task"]
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("Summary", task["summary"], render_context)
        print_key_value("State", task["state"], render_context)
        print_key_value("Workflow Class", task["workflow_class"], render_context)
        return 0

    if verb == "assign":
        task = result["task"]
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("State", task["state"], render_context)
        if isinstance(decision_rights, dict):
            print_key_value("Decision Rights", decision_rights["decision_class"], render_context)
            confirmation = decision_rights_confirmation_label(decision_rights)
            if confirmation is not None:
                print_key_value("Confirmation", confirmation, render_context)
        print_key_value("Worker", result["selected_worker_id"], render_context)
        print_key_value("Lease", result["lease_id"], render_context)
        for line in secret_resolution_lines(result.get("secret_resolution")):
            print(line)
        return 0

    if verb == "close":
        task = result["task"]
        lease = result["lease"]
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("State", task["state"], render_context)
        print_key_value("Lease", f"{lease['lease_id']} ({lease['state']})", render_context)
        print_key_value("Locks Released", len(result["locks"]), render_context)
        print_key_value("Event ID", event["event_id"], render_context)
        if result.get("checkpoint_id"):
            print_key_value("Checkpoint", result["checkpoint_id"], render_context)
        if result.get("decision_event_id"):
            print_key_value("Decision Event", result["decision_event_id"], render_context)
        print_key_value(
            "Controller State Changed",
            "yes" if result.get("controller_state_changed") else "no",
            render_context,
        )
        if result.get("next_action"):
            print_key_value("Next Action", result["next_action"], render_context)
        return 0

    if verb == "archive":
        task = result["task"]
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("State", task["state"], render_context)
        print_key_value("Event ID", event["event_id"], render_context)
        if result.get("checkpoint_id"):
            print_key_value("Checkpoint", result["checkpoint_id"], render_context)
        if result.get("decision_event_id"):
            print_key_value("Decision Event", result["decision_event_id"], render_context)
        print_key_value(
            "Controller State Changed",
            "yes" if result.get("controller_state_changed") else "no",
            render_context,
        )
        if result.get("next_action"):
            print_key_value("Next Action", result["next_action"], render_context)
        return 0

    if verb == "checkpoint":
        task = result["task"]
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("State", task["state"], render_context)
        print_key_value("Checkpoint", result["checkpoint_id"], render_context)
        print_key_value("Target Action", result["target_action"], render_context)
        print_key_value("Captured At", result["captured_at"], render_context)
        print_key_value("Event ID", event["event_id"], render_context)
        print_key_value(
            "Controller State Changed",
            "yes" if result.get("controller_state_changed") else "no",
            render_context,
        )
        baseline = format_checkpoint_baseline_summary(result.get("baseline_fingerprint"))
        if baseline:
            print_key_value("Baseline Repo", baseline, render_context)
        evidence_refs = format_evidence_refs(result.get("artifact_refs"))
        if evidence_refs:
            print_key_value("Evidence Refs", evidence_refs, render_context)
        if result.get("next_action"):
            print_key_value("Next Action", result["next_action"], render_context)
        return 0

    if verb in {"pause", "resume", "reroute"}:
        task = result["task"]
        lease = result.get("lease")
        print_key_value("Task", task["task_id"], render_context)
        print_key_value("State", task["state"], render_context)
        if isinstance(decision_rights, dict):
            print_key_value("Decision Rights", decision_rights["decision_class"], render_context)
            confirmation = decision_rights_confirmation_label(decision_rights)
            if confirmation is not None:
                print_key_value("Confirmation", confirmation, render_context)
        if lease is not None:
            print_key_value("Lease", f"{lease['lease_id']} ({lease['state']})", render_context)
        if verb == "reroute":
            print_key_value("Worker", result["selected_worker_id"], render_context)
            previous_lease_id = result.get("previous_lease_id")
            if previous_lease_id:
                print_key_value("Previous Lease", previous_lease_id, render_context)
        print_key_value("Event ID", event["event_id"], render_context)
        print_key_value(
            "Controller State Changed",
            "yes" if result.get("controller_state_changed") else "no",
            render_context,
        )
        if lease.get("intervention_reason"):
            print_key_value("Intervention Basis", lease["intervention_reason"], render_context)
        runtime_intervention = result.get("runtime_intervention")
        if isinstance(runtime_intervention, dict):
            print_key_value("Runtime Pause Depth", runtime_intervention["status"], render_context)
        if result.get("next_action"):
            print_key_value("Next Action", result["next_action"], render_context)
        for warning in action.get("warnings", []):
            print(f"Warning: {warning}")
        return 0

    return 0


def emit_task_action_error(
    args: argparse.Namespace,
    verb: str,
    *,
    message: str,
    code: str = "internal_error",
    exit_code: int = 1,
    result: dict[str, object] | None = None,
    event: dict[str, object] | None = None,
) -> int:
    payload = {
        "ok": False,
        "command": f"macs task {verb}",
        "timestamp": action_timestamp(),
        "warnings": [],
        "errors": [
            {
                "code": code,
                "message": message,
            }
        ],
        "data": {
            "result": result or {},
            "event": event,
        },
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        emit_action_error_human(message, payload["data"]["result"])
    return exit_code


def emit_recovery_action_result(args: argparse.Namespace, verb: str, action: dict[str, object]) -> int:
    event = action["event"]
    payload = {
        "ok": True,
        "command": f"macs recovery {verb}",
        "timestamp": event["timestamp"],
        "warnings": action.get("warnings", []),
        "errors": [],
        "data": {
            "result": action["result"],
            "recovery_run": action.get("recovery_run"),
            "event": event,
        },
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    result = action["result"]
    recovery_run = action.get("recovery_run") or {}
    decision_rights = result.get("decision_rights")
    print(f"Event ID: {event['event_id']}")
    if isinstance(decision_rights, dict):
        print(f"Decision Rights: {decision_rights['decision_class']}")
        confirmation = decision_rights_confirmation_label(decision_rights)
        if confirmation is not None:
            print(f"Confirmation: {confirmation}")
    print(f"Recovery Run: {recovery_run.get('recovery_run_id', 'none')}")
    print(f"State: {recovery_run.get('state', 'unknown')}")
    if isinstance(result.get("task"), dict):
        print(f"Task: {result['task']['task_id']}")
        print(f"Task State: {result['task']['state']}")
    if isinstance(result.get("lease"), dict):
        print(f"Lease: {result['lease']['lease_id']} ({result['lease']['state']})")
    if "controller_state_changed" in result:
        print(f"Controller State Changed: {'yes' if result.get('controller_state_changed') else 'no'}")
    if result.get("next_action"):
        print(f"Next Action: {result['next_action']}")
    return 0


def emit_recovery_action_error(
    args: argparse.Namespace,
    verb: str,
    *,
    message: str,
    code: str,
    exit_code: int,
    result: dict[str, object] | None = None,
    event: dict[str, object] | None = None,
) -> int:
    payload = {
        "ok": False,
        "command": f"macs recovery {verb}",
        "timestamp": action_timestamp(),
        "warnings": [],
        "errors": [{"code": code, "message": message}],
        "data": {
            "result": result or {},
            "event": event,
        },
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        emit_action_error_human(message, payload["data"]["result"])
    return exit_code


def emit_lock_action_error(
    args: argparse.Namespace,
    verb: str,
    *,
    message: str,
    code: str,
    exit_code: int,
    result: dict[str, object] | None = None,
) -> int:
    payload = {
        "ok": False,
        "command": f"macs lock {verb}",
        "timestamp": action_timestamp(),
        "warnings": [],
        "errors": [{"code": code, "message": message}],
        "data": {
            "result": result or {},
            "event": None,
        },
    }
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        emit_action_error_human(message, payload["data"]["result"])
    return exit_code


def action_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def task_action_key(verb: str) -> str | None:
    mapping = {
        "assign": "task.assign",
        "pause": "task.pause",
        "resume": "task.resume",
        "reroute": "task.reroute",
        "abort": "task.abort",
    }
    return mapping.get(verb)


def recovery_action_key(verb: str) -> str | None:
    mapping = {
        "retry": "recovery.retry",
        "reconcile": "recovery.reconcile",
    }
    return mapping.get(verb)


def decision_rights_error_result(
    decision_rights: dict[str, object],
    *,
    affected_refs: dict[str, object] | None = None,
    next_action: str | None = None,
) -> dict[str, object]:
    return action_result_with_decision_rights(
        {},
        decision_rights,
        controller_state_changed=False,
        affected_refs=affected_refs,
        next_action=next_action,
    )


def task_confirm_next_action(args: argparse.Namespace) -> str:
    command = [f"macs task {args.verb}", f"--task {args.task_id}", "--confirm"]
    worker_id = getattr(args, "worker_id", None)
    workflow_class = getattr(args, "workflow_class", None)
    rationale = getattr(args, "rationale", None)
    if worker_id:
        command.append(f"--worker {worker_id}")
    if workflow_class:
        command.append(f"--workflow-class {workflow_class}")
    if rationale:
        command.append(f"--rationale {rationale}")
    return " ".join(command)


def recovery_confirm_next_action(args: argparse.Namespace) -> str:
    command = [f"macs recovery {args.verb}", f"--task {args.task_id}", "--confirm"]
    rationale = getattr(args, "rationale", None)
    if rationale:
        command.append(f"--rationale {rationale}")
    return " ".join(command)


def worker_inspect_warnings(worker: dict[str, object]) -> list[str]:
    warnings = []
    if worker["state"] in {"degraded", "unavailable", "quarantined"}:
        warnings.append(
            f"Worker {worker['worker_id']} is {worker['state']}; controller truth remains authoritative."
        )
    if worker.get("adapter_probe_warning"):
        warnings.append(f"Adapter probe unavailable: {worker['adapter_probe_warning']}")
    pane_warning = pane_navigation_warning(worker.get("pane_navigation"))
    if pane_warning is not None:
        warnings.append(pane_warning)
    return warnings


def task_inspect_warnings(task: dict[str, object]) -> list[str]:
    warnings = []
    current_owner = task["controller_truth"]["current_owner"]
    if current_owner and current_owner["state"] in {"degraded", "unavailable", "quarantined"}:
        warnings.append(
            f"Task {task['task_id']} is attached to {current_owner['state']} worker {current_owner['worker_id']}."
        )
    if task.get("adapter_probe_warning"):
        warnings.append(f"Adapter probe unavailable: {task['adapter_probe_warning']}")
    warnings.extend(runtime_intervention_warnings(task.get("runtime_intervention")))
    pane_warning = pane_navigation_warning(task.get("pane_navigation"))
    if pane_warning is not None:
        warnings.append(pane_warning)
    return warnings


def lease_inspect_runtime_intervention(
    state_db: Path,
    lease: dict[str, object],
) -> dict[str, object] | None:
    if lease.get("state") != "paused" or not lease.get("worker_id"):
        return None
    try:
        worker = inspect_worker(state_db, str(lease["worker_id"]))
    except WorkerNotFoundError:
        return None
    return build_runtime_pause_resume_status(worker, action="pause")


def normalize_tmux_socket(socket_path: str | None) -> str | None:
    if not socket_path:
        return None
    return str(Path(socket_path).expanduser().resolve(strict=False))


def current_tmux_socket() -> str | None:
    if not os.environ.get("TMUX"):
        return None
    result = subprocess.run(
        ["tmux", "display-message", "-p", "#{socket_path}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def pane_navigation_warning(pane_navigation: object) -> str | None:
    if not isinstance(pane_navigation, dict) or pane_navigation.get("status") != "pinned_only":
        return None
    tmux_session = pane_navigation.get("tmux_session")
    tmux_pane = pane_navigation.get("tmux_pane")
    if tmux_session and tmux_pane:
        return f"Unable to open tmux pane live; pinned target {tmux_session} {tmux_pane} for follow-up."
    return "Unable to open tmux pane live; no pane target was available to pin."


def print_key_value(label: str, value: object, render_context) -> None:
    for line in key_value_lines(label, value, render_context):
        print(line)


def pin_target_pane(repo_root: Path, pane_target: dict[str, object] | None) -> None:
    if not pane_target or not pane_target.get("tmux_pane"):
        return
    script_path = Path(__file__).resolve().parents[2] / "tmux_bridge" / "set_target.sh"
    command = [str(script_path), "--pane", str(pane_target["tmux_pane"])]
    if pane_target.get("tmux_session"):
        command.extend(["--session", str(pane_target["tmux_session"])])
    if pane_target.get("tmux_socket"):
        command.extend(["--socket", str(pane_target["tmux_socket"])])
    env = os.environ.copy()
    env["MACS_REPO_ROOT"] = str(repo_root)
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Failed to pin tmux target pane")


def open_pane_target(repo_root: Path, pane_target: dict[str, object] | None) -> dict[str, object]:
    pane_navigation = {
        "status": "pinned_only",
        "tmux_socket": pane_target.get("tmux_socket") if pane_target else None,
        "tmux_session": pane_target.get("tmux_session") if pane_target else None,
        "tmux_pane": pane_target.get("tmux_pane") if pane_target else None,
    }
    if not pane_target or not pane_target.get("tmux_pane"):
        return pane_navigation

    pin_target_pane(repo_root, pane_target)

    current_socket = current_tmux_socket()
    if current_socket is None:
        return pane_navigation

    target_socket = pane_target.get("tmux_socket")
    if target_socket and normalize_tmux_socket(current_socket) != normalize_tmux_socket(str(target_socket)):
        return pane_navigation

    command = ["tmux"]
    if target_socket:
        command.extend(["-S", str(target_socket)])
    result = subprocess.run(
        command + ["select-pane", "-t", str(pane_target["tmux_pane"])],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        pane_navigation["status"] = "opened"
    return pane_navigation


def render_adapter_evidence_lines(evidence: list[dict[str, object]]) -> list[str]:
    lines = ["Adapter Evidence:"]
    if not evidence:
        lines.append("- none")
        return lines
    for item in evidence:
        lines.append(
            f"- {item['kind']} {item['name']} "
            f"confidence={item['confidence']} freshness={item['freshness_seconds']}s"
        )
    return lines


def format_affected_refs(affected_refs: object) -> str | None:
    if not isinstance(affected_refs, dict):
        return None
    label_map = {
        "lock_id": "lock",
        "task_id": "task",
        "lease_id": "lease",
        "worker_id": "worker",
        "surface_id": "surface",
        "secret_ref": "secret_ref",
        "recovery_run_id": "recovery",
        "replacement_lease_id": "replacement_lease",
        "previous_lease_id": "previous_lease",
        "predecessor_lease_id": "predecessor_lease",
        "selected_worker_id": "selected_worker",
    }
    parts = []
    for key in (
        "lock_id",
        "task_id",
        "lease_id",
        "worker_id",
        "surface_id",
        "secret_ref",
        "recovery_run_id",
        "replacement_lease_id",
        "previous_lease_id",
        "predecessor_lease_id",
        "selected_worker_id",
    ):
        value = affected_refs.get(key)
        if value is not None:
            parts.append(f"{label_map[key]}={value}")
    return " ".join(parts) if parts else None


def format_evidence_refs(evidence_refs: object) -> str | None:
    if not isinstance(evidence_refs, dict):
        return None
    preferred_keys = (
        "bundle_dir",
        "metadata_json",
        "head_ref",
        "git_status",
        "git_diff",
        "git_diff_cached",
    )
    parts = []
    for key in preferred_keys:
        value = evidence_refs.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    return " ".join(parts) if parts else None


def format_checkpoint_baseline_summary(baseline_fingerprint: object) -> str | None:
    if not isinstance(baseline_fingerprint, dict):
        return None
    head = baseline_fingerprint.get("head") or {}
    dirty_state = baseline_fingerprint.get("dirty_state") or {}
    affected_paths = baseline_fingerprint.get("affected_paths") or []
    parts = [f"head_state={head.get('state') or 'unknown'}"]
    if head.get("oid"):
        parts.append(f"head_oid={str(head['oid'])[:12]}")
    if head.get("ref"):
        parts.append(f"head_ref={head['ref']}")
    parts.append(f"tracked_changes={dirty_state.get('tracked_change_count', 0)}")
    parts.append(f"untracked={dirty_state.get('untracked_count', 0)}")
    parts.append(f"paths={len(affected_paths)}")
    return " ".join(parts)


def render_checkpoint_ref_line(checkpoint: dict[str, object]) -> str:
    segments = [
        str(checkpoint.get("checkpoint_id") or "unknown"),
        str(checkpoint.get("target_action") or "unknown"),
        f"actor={checkpoint.get('actor_id') or 'unknown'}",
        f"captured={checkpoint.get('captured_at') or 'unknown'}",
    ]
    if checkpoint.get("event_id"):
        segments.append(f"event={checkpoint['event_id']}")
    if checkpoint.get("decision_event_id"):
        segments.append(f"decision={checkpoint['decision_event_id']}")
    baseline = format_checkpoint_baseline_summary(checkpoint.get("baseline_fingerprint"))
    if baseline:
        segments.append(baseline)
    evidence_refs = format_evidence_refs(checkpoint.get("evidence_refs"))
    if evidence_refs:
        segments.append(evidence_refs)
    return "  ".join(segments)


def format_governance_policy_trace(policy: object) -> str | None:
    if not isinstance(policy, dict):
        return None
    snapshot = policy.get("snapshot") or {}
    parts = [
        f"version={policy.get('policy_version') or 'unknown'}",
        f"path={policy.get('policy_path') or 'unknown'}",
    ]
    if isinstance(snapshot, dict) and snapshot.get("snapshot_id"):
        parts.append(f"snapshot={snapshot['snapshot_id']}")
        if snapshot.get("traceability_status"):
            parts.append(f"traceability={snapshot['traceability_status']}")
    return " ".join(parts)


def governance_evidence_lines(evidence: object) -> list[str]:
    if not isinstance(evidence, dict):
        return []
    lines = ["Governance Evidence:"]
    policy_trace = format_governance_policy_trace(evidence.get("policy"))
    if policy_trace:
        lines.append(f"Policy Traceability: {policy_trace}")

    routing = evidence.get("routing")
    if isinstance(routing, dict):
        segments = [
            f"decision={routing.get('decision_id') or 'unknown'}",
            f"worker={routing.get('selected_worker_id') or 'none'}",
        ]
        if routing.get("related_event_id"):
            segments.append(f"event={routing['related_event_id']}")
        lines.append(f"Routing Evidence: {' '.join(segments)}")

    version_pins = evidence.get("version_pins")
    if isinstance(version_pins, dict) and version_pins.get("surface_results"):
        lines.append("Version Pin Evidence:")
        for surface in version_pins["surface_results"]:
            if not isinstance(surface, dict):
                continue
            selector_context = surface.get("selector_context") or {}
            expected = surface.get("expected") or {}
            observed = format_surface_version_observed({"observed": surface.get("observed")})
            expected_runtime = ",".join(expected.get("runtime_identities", [])) or "none"
            expected_model = ",".join(expected.get("model_identities", [])) or "none"
            segments = [
                f"- {surface.get('surface_id') or 'unknown'}: {surface.get('outcome') or 'unknown'}",
                f"expected=runtime={expected_runtime} model={expected_model}",
                f"observed={observed}",
                (
                    "selector="
                    f"adapter={selector_context.get('adapter_id')} "
                    f"workflow={selector_context.get('workflow_class')} "
                    f"profile={selector_context.get('operating_profile')}"
                ),
            ]
            if surface.get("reason"):
                segments.append(f"reason={surface['reason']}")
            if surface.get("routing_decision_id"):
                segments.append(f"route={surface['routing_decision_id']}")
            if surface.get("related_event_id"):
                segments.append(f"event={surface['related_event_id']}")
            lines.append(" ".join(segments))

    secret_scope = evidence.get("secret_scope")
    if isinstance(secret_scope, dict) and secret_scope.get("surface_results"):
        lines.append("Secret Scope Evidence:")
        for surface in secret_scope["surface_results"]:
            if not isinstance(surface, dict):
                continue
            selector_context = surface.get("selector_context") or {}
            secret_refs = ",".join(str(item) for item in surface.get("secret_refs", [])) or "none"
            segments = [
                f"- {surface.get('surface_id') or 'unknown'}: {surface.get('outcome') or 'unknown'}",
                f"secret_ref={secret_refs}",
                (
                    "selector="
                    f"adapter={selector_context.get('adapter_id')} "
                    f"workflow={selector_context.get('workflow_class')} "
                    f"profile={selector_context.get('operating_profile')}"
                ),
            ]
            if surface.get("reason"):
                segments.append(f"reason={surface['reason']}")
            if surface.get("routing_decision_id"):
                segments.append(f"route={surface['routing_decision_id']}")
            if surface.get("related_event_id"):
                segments.append(f"event={surface['related_event_id']}")
            lines.append(" ".join(segments))

    checkpoint = evidence.get("checkpoint")
    if isinstance(checkpoint, dict):
        segments = [
            str(checkpoint.get("checkpoint_id") or "none"),
            str(checkpoint.get("target_action") or "unknown"),
            f"actor={checkpoint.get('actor_id') or 'unknown'}",
        ]
        if checkpoint.get("captured_at"):
            segments.append(f"captured={checkpoint['captured_at']}")
        if checkpoint.get("event_id"):
            segments.append(f"event={checkpoint['event_id']}")
        if checkpoint.get("decision_event_id"):
            segments.append(f"decision={checkpoint['decision_event_id']}")
        if checkpoint.get("baseline_summary"):
            segments.append(str(checkpoint["baseline_summary"]))
        evidence_refs = format_evidence_refs(checkpoint.get("evidence_refs"))
        if evidence_refs:
            segments.append(evidence_refs)
        lines.append("Checkpoint Evidence:")
        lines.append(f"- {' '.join(segments)}")

    decision_event = evidence.get("decision_event")
    if isinstance(decision_event, dict):
        segments = [
            f"event={decision_event.get('event_id') or 'unknown'}",
            f"actor={decision_event.get('actor_id') or 'unknown'}",
        ]
        if decision_event.get("decision_action"):
            segments.append(f"action={decision_event['decision_action']}")
        if decision_event.get("checkpoint_id"):
            segments.append(f"checkpoint={decision_event['checkpoint_id']}")
        lines.append(f"Decision Linkage: {' '.join(segments)}")
    return lines


def load_active_governance_policy(
    repo_root: Path,
    *,
    persist_sanitized: bool = True,
) -> tuple[Path, dict[str, object]]:
    policy_path = governance_policy_path(repo_root / ".codex" / "orchestration")
    return policy_path, load_governance_policy(policy_path, persist_sanitized=persist_sanitized)


def governance_summary_for_worker(
    repo_root: Path,
    worker: dict[str, object],
    *,
    workflow_class: str | None = None,
    adapter_evidence: list[dict[str, object]] | None = None,
    registration_scope: bool = False,
    persist_sanitized: bool = True,
) -> dict[str, object]:
    policy_path, governance_policy = load_active_governance_policy(
        repo_root,
        persist_sanitized=persist_sanitized,
    )
    adapter_descriptor = get_adapter(str(worker["adapter_id"])).descriptor()
    summary = evaluate_worker_governance(
        worker,
        adapter_descriptor,
        governance_policy,
        workflow_class=workflow_class,
        adapter_evidence=adapter_evidence,
        enforce_surface_version_pins=adapter_evidence is not None,
        registration_scope=registration_scope,
    )
    summary["policy_path"] = str(policy_path)
    return summary


def adapter_governance_summary(
    repo_root: Path,
    adapter_descriptor: dict[str, object],
    *,
    workflow_class: str | None = None,
) -> dict[str, object]:
    policy_path, governance_policy = load_active_governance_policy(repo_root)
    declared_surface_ids = []
    for surface_id in adapter_descriptor.get("governed_surfaces", []):
        value = str(surface_id).strip()
        if value:
            declared_surface_ids.append(value)
    summary = describe_adapter_governance(
        adapter_descriptor,
        governance_policy,
        workflow_class=workflow_class,
    )
    summary["policy_path"] = str(policy_path)
    summary["active_snapshot"] = active_governance_snapshot(
        build_paths(repo_root).state_db,
        live_policy=governance_policy,
        workflow_class=workflow_class,
        adapter_id=str(adapter_descriptor["adapter_id"]),
        surface_ids=declared_surface_ids,
    )
    return summary


def format_governance_summary(governance: object) -> str | None:
    if not isinstance(governance, dict):
        return None
    active_surfaces = governance.get("active_surfaces") or []
    if not active_surfaces:
        return "none"
    blocked = {item["surface_id"]: item["reason"] for item in governance.get("blocked_surfaces", [])}
    parts = []
    for surface_id in active_surfaces:
        reason = blocked.get(surface_id)
        if reason:
            parts.append(f"{surface_id} (blocked: {reason})")
        else:
            parts.append(f"{surface_id} (allowed)")
    return ", ".join(parts)


def surface_version_enforcement_lines(summary: object) -> list[str]:
    if not isinstance(summary, dict):
        return []
    blocked_surfaces = summary.get("blocked_surfaces") or []
    evaluated_surfaces = summary.get("evaluated_surfaces") or []
    if summary.get("effective_state") == "none_configured":
        return []
    if summary.get("evaluation_state") == "probe_required":
        return ["Surface Version Enforcement: probe required for applicable pins"]
    if not evaluated_surfaces:
        return []
    lines = ["Surface Version Enforcement:"]
    for surface in evaluated_surfaces:
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("surface_id", "unknown")
        blocked = next((item for item in blocked_surfaces if item.get("surface_id") == surface_id), None)
        if isinstance(blocked, dict):
            lines.append(
                f"- {surface_id}: blocked {blocked.get('reason')} "
                f"expected={format_surface_version_expectations(blocked)} "
                f"observed={format_surface_version_observed(blocked)}"
            )
        else:
            lines.append(
                f"- {surface_id}: matched expected={format_surface_version_expectations(surface)} "
                f"observed={format_surface_version_observed(surface)}"
            )
    return lines


def surface_version_pin_summary_lines(version_pins: object, *, label: str = "Surface version pins") -> list[str]:
    if not isinstance(version_pins, dict):
        return []
    state = version_pins.get("state")
    effective_state = version_pins.get("effective_state")
    effective_pins = version_pins.get("effective_pins") or []
    if state == "none_configured":
        return [f"{label}: none configured"]
    if effective_state == "no_matching_pins":
        return [f"{label}: configured, but none apply to the current inspection context"]
    if not effective_pins:
        return [f"{label}: configured"]
    lines = [f"{label}:"]
    for pin in effective_pins:
        if isinstance(pin, dict):
            lines.append(f"- {format_surface_version_pin(pin)}")
    return lines


def secret_scope_summary_lines(secret_scopes: object, *, label: str = "Secret scopes") -> list[str]:
    if not isinstance(secret_scopes, dict):
        return []
    state = secret_scopes.get("state")
    effective_state = secret_scopes.get("effective_state")
    effective_scopes = secret_scopes.get("effective_scopes") or []
    if state == "none_configured":
        return [f"{label}: none configured"]
    if effective_state == "no_matching_scopes":
        return [f"{label}: configured, but none apply to the current inspection context"]
    if not effective_scopes:
        return [f"{label}: configured"]
    lines = [f"{label}:"]
    for scope in effective_scopes:
        if isinstance(scope, dict):
            lines.append(f"- {format_secret_scope(scope)}")
    return lines


def format_governance_snapshot_reference(snapshot: object) -> str:
    if not isinstance(snapshot, dict):
        return "none"
    snapshot_id = str(snapshot.get("snapshot_id") or "none")
    traceability_status = snapshot.get("traceability_status")
    if traceability_status == "matches_live_policy":
        return f"{snapshot_id} (matches live governance policy)"
    if traceability_status == "stale_vs_live_policy":
        return f"{snapshot_id} (stale relative to live governance policy)"
    if traceability_status == "snapshot_record_missing":
        return f"{snapshot_id} (snapshot record missing)"
    return snapshot_id


def format_surface_version_pin(pin: dict[str, object]) -> str:
    runtime_identity = pin.get("expected_runtime_identity") or "none"
    model_identity = pin.get("expected_model_identity") or "none"
    return (
        f"surface={pin.get('surface_id')} "
        f"adapter={pin.get('adapter_id')} "
        f"workflow={pin.get('workflow_class')} "
        f"profile={pin.get('operating_profile')} "
        f"runtime={runtime_identity} "
        f"model={model_identity}"
    )


def format_secret_scope(scope: dict[str, object]) -> str:
    parts = [
        f"surface={scope.get('surface_id')}",
        f"adapter={scope.get('adapter_id')}",
        f"workflow={scope.get('workflow_class')}",
        f"profile={scope.get('operating_profile')}",
        f"secret_ref={scope.get('secret_ref')}",
    ]
    if scope.get("display_name"):
        parts.append(f"display={scope['display_name']}")
    parts.append(f"redaction={scope.get('redaction_label') or 'redacted'}")
    return " ".join(parts)


def secret_resolution_lines(secret_resolution: object, *, label: str = "Secret Resolution") -> list[str]:
    if not isinstance(secret_resolution, dict):
        return []
    status = str(secret_resolution.get("status") or "")
    if not status or status == "not_required":
        return []
    lines = [f"{label}: {status}"]
    for surface in secret_resolution.get("surface_summaries", []):
        if not isinstance(surface, dict):
            continue
        refs = surface.get("resolved_secret_refs") or surface.get("required_secret_refs") or surface.get("unresolved_secret_refs") or []
        selector_context = surface.get("selector_context") or {}
        selector_bits = [
            f"adapter={selector_context.get('adapter_id')}",
            f"workflow={selector_context.get('workflow_class')}",
            f"profile={selector_context.get('operating_profile')}",
        ]
        refs_label = ",".join(str(item) for item in refs) if refs else "none"
        reason = surface.get("reason")
        if reason:
            lines.append(
                f"- {surface.get('surface_id')}: blocked {reason} "
                f"secret_ref={refs_label} {' '.join(selector_bits)}"
            )
        else:
            lines.append(
                f"- {surface.get('surface_id')}: resolved secret_ref={refs_label} "
                f"{' '.join(selector_bits)} delivery={surface.get('delivery_mode')}"
            )
    return lines


def format_surface_version_expectations(surface: dict[str, object]) -> str:
    pins = surface.get("applicable_pins") or []
    runtime_values = sorted({str(pin.get("expected_runtime_identity")) for pin in pins if pin.get("expected_runtime_identity")})
    model_values = sorted({str(pin.get("expected_model_identity")) for pin in pins if pin.get("expected_model_identity")})
    runtime_label = ",".join(runtime_values) if runtime_values else "none"
    model_label = ",".join(model_values) if model_values else "none"
    return f"runtime={runtime_label} model={model_label}"


def format_surface_version_observed(surface: dict[str, object]) -> str:
    observed = surface.get("observed") or {}
    runtime = observed.get("runtime_identity") or {}
    model = observed.get("model_identity") or {}
    runtime_identity = runtime.get("identity") or "none"
    model_identity = model.get("identity") or "none"
    confidence = model.get("confidence") or runtime.get("confidence") or "unknown"
    freshness = model.get("freshness_seconds")
    if freshness is None:
        freshness = runtime.get("freshness_seconds")
    source_ref = model.get("source_ref") or runtime.get("source_ref") or "unknown"
    freshness_label = f"{freshness}s" if freshness is not None else "unknown"
    return (
        f"runtime={runtime_identity} model={model_identity} "
        f"confidence={confidence} freshness={freshness_label} source={source_ref}"
    )


def routing_rejection_lines(routing_evaluation: object) -> list[str]:
    if not isinstance(routing_evaluation, dict):
        return []
    rejected_workers = routing_evaluation.get("rejected_workers")
    if not isinstance(rejected_workers, list) or not rejected_workers:
        return []
    lines = ["Routing Rejections:"]
    for worker in rejected_workers:
        reasons = ", ".join(worker.get("reasons", [])) or "none"
        lines.append(f"- {worker['worker_id']}: {reasons}")
    return lines


def worker_registration_block_message(
    *,
    worker_id: str,
    governance: dict[str, object],
    policy_path: object,
) -> tuple[str, str]:
    summary = governance.get("surface_version_pins") if isinstance(governance, dict) else {}
    blocked_surfaces = summary.get("blocked_surfaces") if isinstance(summary, dict) else []
    reason_labels = []
    for prefix, label in (
        ("surface_version_pin_mismatch", "mismatch"),
        ("surface_version_evidence_missing", "missing evidence"),
        ("surface_version_evidence_stale", "stale evidence"),
        ("surface_version_evidence_untrusted", "low-trust evidence"),
    ):
        if any(isinstance(item, dict) and str(item.get("reason", "")).startswith(prefix) for item in blocked_surfaces or []):
            reason_labels.append(label)
    suffix = f" ({', '.join(reason_labels)})" if reason_labels else ""
    policy_ref = str(policy_path) if policy_path else "governance policy"
    message = (
        f"Worker {worker_id} was quarantined during registration because surface version pin enforcement "
        f"blocked ready-state promotion{suffix}"
    )
    next_action = f"inspect worker {worker_id}, review {policy_ref}, refresh trustworthy runtime or model evidence, then retry registration"
    return message, next_action


def audit_content_lines(event: dict[str, object]) -> list[str]:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return []
    audit_content = payload.get("audit_content")
    if not isinstance(audit_content, dict):
        return []
    lines = ["Audit Content:"]
    for content_kind, details in audit_content.items():
        if not isinstance(details, dict):
            continue
        lines.append(f"- {content_kind}: {details.get('status', 'unknown')}")
    return lines


def render_event_ref_line(event: dict[str, object]) -> str:
    segments = [event["event_id"], event["event_type"]]
    if event.get("actor_id"):
        segments.append(f"actor={event['actor_id']}")
    if event.get("checkpoint_id"):
        segments.append(f"checkpoint={event['checkpoint_id']}")
    if event.get("target_action"):
        segments.append(f"target={event['target_action']}")
    if event.get("decision_event_id"):
        segments.append(f"decision={event['decision_event_id']}")
    if event.get("causation_id"):
        segments.append(f"cause={event['causation_id']}")
    if event.get("intervention_rationale"):
        segments.append(f"rationale={event['intervention_rationale']}")
    affected_refs = format_affected_refs(event.get("affected_refs"))
    if affected_refs:
        segments.append(affected_refs)
    if event.get("redaction_level") and event["redaction_level"] != "none":
        segments.append(f"redaction={event['redaction_level']}")
    return "  ".join(segments)


def emit_worker_inspect_human_readable(worker: dict[str, object]) -> None:
    controller_truth = worker["controller_truth"]
    render_context = terminal_render_context()
    print_key_value("Worker", worker["worker_id"], render_context)
    print_key_value("Runtime", worker["runtime_type"], render_context)
    print_key_value("State", worker["state"], render_context)
    governance_summary = format_governance_summary(worker.get("governance"))
    if governance_summary is not None:
        print_key_value("Governed Surfaces", governance_summary, render_context)
    for line in surface_version_enforcement_lines((worker.get("governance") or {}).get("surface_version_pins")):
        print(line)
    for warning in worker_inspect_warnings(worker):
        print(f"Warning: {warning}")
    print("Controller Truth:")
    print_key_value("Canonical State", controller_truth["canonical_state"], render_context)
    print_key_value(
        "Routability",
        f"{'assignable' if controller_truth['routability']['assignable'] else 'blocked'} "
        f"({controller_truth['routability']['reason']})",
        render_context,
    )
    current_task = controller_truth["current_task"]
    if current_task is None:
        print_key_value("Current Task", "none", render_context)
    else:
        print_key_value("Current Task", f"{current_task['task_id']} ({current_task['state']})", render_context)
    current_lease = controller_truth["current_lease"]
    if current_lease is None:
        print_key_value("Current Lease", "none", render_context)
    else:
        print_key_value(
            "Current Lease",
            f"{current_lease['lease_id']} ({current_lease['state']})",
            render_context,
        )
        if current_lease.get("intervention_reason"):
            print_key_value("Intervention Basis", current_lease["intervention_reason"], render_context)
    if worker.get("blocking_condition"):
        print_key_value("Blocking Condition", worker["blocking_condition"], render_context)
    if worker.get("next_action"):
        print_key_value("Next Action", worker["next_action"], render_context)
    print("Recent Events:")
    for event in controller_truth["recent_event_refs"]:
        print(render_event_ref_line(event))
    pane_target = controller_truth["pane_target"]
    print_key_value("Pane Target", f"{pane_target['tmux_session']} {pane_target['tmux_pane']}", render_context)
    pane_navigation = worker.get("pane_navigation")
    if pane_navigation is not None:
        print_key_value("Pane Open", pane_navigation["status"], render_context)
    for line in render_adapter_evidence_lines(worker.get("adapter_evidence", [])):
        print(line)


def emit_task_inspect_human_readable(task: dict[str, object]) -> None:
    controller_truth = task["controller_truth"]
    render_context = terminal_render_context()
    print_key_value("Task", task["task_id"], render_context)
    print_key_value("Summary", task["summary"], render_context)
    print_key_value("State", task["state"], render_context)
    governance_summary = format_governance_summary(task.get("governance"))
    if governance_summary is not None:
        print_key_value("Governed Surfaces", governance_summary, render_context)
    for line in surface_version_enforcement_lines((task.get("governance") or {}).get("surface_version_pins")):
        print(line)
    for line in secret_resolution_lines(task.get("secret_resolution")):
        print(line)
    for warning in task_inspect_warnings(task):
        print(f"Warning: {warning}")
    print("Controller Truth:")
    current_owner = controller_truth["current_owner"]
    if current_owner is None:
        print_key_value("Current Owner", "none", render_context)
    else:
        print_key_value(
            "Current Owner",
            f"{current_owner['worker_id']} ({current_owner['state']}, {current_owner['runtime_type']})",
            render_context,
        )
    current_lease = controller_truth["current_lease"]
    if current_lease is None:
        print_key_value("Current Lease", "none", render_context)
    else:
        print_key_value(
            "Current Lease",
            f"{current_lease['lease_id']} ({current_lease['state']})",
            render_context,
        )
        if current_lease.get("intervention_reason"):
            print_key_value("Intervention Basis", current_lease["intervention_reason"], render_context)
    recovery_run = controller_truth.get("recovery_run")
    if recovery_run is not None:
        print_key_value(
            "Recovery Run",
            f"{recovery_run['recovery_run_id']} ({recovery_run['state']})",
            render_context,
        )
    if task.get("blocking_condition"):
        print_key_value("Blocking Condition", task["blocking_condition"], render_context)
    runtime_intervention = task.get("runtime_intervention")
    if isinstance(runtime_intervention, dict):
        print_key_value("Runtime Pause Depth", runtime_intervention["status"], render_context)
    if task.get("next_action"):
        print_key_value("Next Action", task["next_action"], render_context)
    print_key_value("Lock Summary", f"{controller_truth['lock_summary']['active_lock_count']} active", render_context)
    for lock in controller_truth["lock_summary"]["locks"]:
        print(f"{lock['lock_id']}  {lock['target_ref']}  {lock['state']}")
    routing = controller_truth["routing_rationale_summary"]
    if routing is None:
        print_key_value("Routing Rationale", "none", render_context)
    else:
        print_key_value(
            "Routing Rationale",
            f"{routing['decision_id']} -> {routing['selected_worker_id']}",
            render_context,
        )
        if routing.get("rationale"):
            print_key_value("Routing Summary", routing["rationale"], render_context)
    for line in routing_rejection_lines((task.get("routing_decision") or {}).get("rationale")):
        print(line)
    for line in governance_evidence_lines(task.get("governance_evidence")):
        print(line)
    recent_checkpoints = controller_truth.get("recent_checkpoint_refs") or []
    if recent_checkpoints:
        print("Recent Checkpoints:")
        for checkpoint in recent_checkpoints:
            print(render_checkpoint_ref_line(checkpoint))
    print("Recent Events:")
    for event in controller_truth["recent_event_refs"]:
        print(render_event_ref_line(event))
    pane_target = controller_truth["pane_target"]
    if pane_target is None:
        print_key_value("Pane Target", "none", render_context)
    else:
        print_key_value("Pane Target", f"{pane_target['tmux_session']} {pane_target['tmux_pane']}", render_context)
    pane_navigation = task.get("pane_navigation")
    if pane_navigation is not None:
        print_key_value("Pane Open", pane_navigation["status"], render_context)
    for line in render_adapter_evidence_lines(task.get("adapter_evidence", [])):
        print(line)


def emit_lease_inspect_human_readable(
    lease: dict[str, object],
    runtime_intervention: dict[str, object] | None,
    blocking_condition: str | None,
    next_action: str | None,
    decision_event: dict[str, object] | None = None,
    recent_event_refs: list[dict[str, object]] | None = None,
) -> None:
    render_context = terminal_render_context()
    print_key_value("Lease", lease["lease_id"], render_context)
    print_key_value("Task", lease["task_id"], render_context)
    print_key_value("Worker", lease["worker_id"], render_context)
    print_key_value("State", lease["state"], render_context)
    print_key_value("Issued At", lease["issued_at"], render_context)
    print_key_value("Accepted At", lease["accepted_at"] or "none", render_context)
    print_key_value("Ended At", lease["ended_at"] or "none", render_context)
    print_key_value("Replacement Lease", lease["replacement_lease_id"] or "none", render_context)
    if lease.get("intervention_reason"):
        print_key_value("Intervention Basis", lease["intervention_reason"], render_context)
    if isinstance(decision_event, dict):
        print_key_value("Decision Event", decision_event["event_id"], render_context)
        print_key_value("Decision Actor", decision_event["actor_id"], render_context)
        if decision_event.get("intervention_rationale"):
            print_key_value("Intervention Rationale", decision_event["intervention_rationale"], render_context)
    if blocking_condition:
        print_key_value("Blocking Condition", blocking_condition, render_context)
    if next_action:
        print_key_value("Next Action", next_action, render_context)
    if isinstance(runtime_intervention, dict):
        print_key_value("Runtime Pause Depth", runtime_intervention["status"], render_context)
        for warning in runtime_intervention_warnings(runtime_intervention):
            print(f"Warning: {warning}")
    if recent_event_refs:
        print("Recent Events:")
        for event in recent_event_refs:
            print(render_event_ref_line(event))


def handle_setup_init(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, store_result, config_result, policy_result, recovery_summary = setup_orchestration(repo_root)
    lock = ControllerSessionLock(paths.controller_lock)
    data = {
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "controller_lock": str(paths.controller_lock),
        "state_db": str(paths.state_db),
        "events_ndjson": str(paths.events_ndjson),
        "state_db_status": "created" if store_result.state_db_created else "verified",
        "events_ndjson_status": "created" if store_result.events_ndjson_created else "verified",
        "controller_defaults": {
            "path": str(config_result.controller_defaults_path),
            "status": "created" if config_result.controller_defaults_path_created else "verified",
        },
        "adapter_settings": {
            "path": str(config_result.adapter_settings_path),
            "status": "created" if config_result.adapter_settings_path_created else "verified",
        },
        "routing_policy": {
            "path": str(policy_result.policy_path),
            "status": "created" if policy_result.policy_path_created else "verified",
            "snapshot_id": policy_result.snapshot_id,
        },
        "governance_policy": {
            "path": str(policy_result.governance_policy_path),
            "status": "created" if policy_result.governance_policy_path_created else "verified",
            "snapshot_id": policy_result.governance_snapshot_id,
        },
        "state_layout": {
            "path": str(config_result.state_layout_path),
            "status": "created" if config_result.state_layout_path_created else "verified",
        },
        "holding_lock": False,
        "startup_summary": recovery_summary.as_dict(),
    }
    snapshot = build_setup_configuration_snapshot(repo_root, paths)
    data["workflow_defaults"] = snapshot["workflow_defaults"]
    data["state_paths"] = snapshot["state_paths"]
    data["compatibility_paths"] = snapshot["compatibility_paths"]

    if not args.exec_cmd:
        return emit_setup_result(args, True, "macs setup init", data, 0)

    cmd = list(args.exec_cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    try:
        lock.acquire(build_lock_metadata(repo_root))
    except SessionLockHeldError as exc:
        message = render_lock_error(exc.info)
        return emit_setup_result(args, False, "macs setup init", {"message": message}, 2)

    data["holding_lock"] = True
    if args.json_output:
        print(json.dumps({"ok": True, "command": "macs setup init", "data": data}, indent=2, sort_keys=True))
    else:
        print("Initialized repo-local orchestration layout.")
        print(f"Orchestration dir: {data['orchestration_dir']}")
        print("Controller session lock acquired; launching controller command.")
    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        lock.release()
        return emit_setup_result(
            args,
            False,
            "macs setup init",
            {"message": f"Unable to exec command: {cmd[0]}"},
            127,
        )


def handle_setup_check(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths = build_paths(repo_root)
    missing = missing_setup_paths(paths)
    if missing:
        return emit_setup_result(
            args,
            False,
            "macs setup check",
            {
                "message": "Repo-local orchestration setup is incomplete. Run 'macs setup init' first.",
                "missing_paths": missing,
            },
            2,
        )

    data = {
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        **build_setup_configuration_snapshot(repo_root, paths),
    }
    return emit_setup_result(args, True, "macs setup check", data, 0)


def handle_setup_validate(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths = build_paths(repo_root)
    missing = missing_setup_paths(paths)
    if missing:
        return emit_setup_result(
            args,
            False,
            "macs setup validate",
            {
                "outcome": "BLOCKED",
                "message": "Repo-local orchestration setup is incomplete. Run 'macs setup init' first.",
                "next_action": "macs setup init",
                "missing_paths": missing,
            },
            2,
        )
    try:
        if getattr(args, "release_gate", False):
            data = run_release_gate(repo_root, paths)
        else:
            data = build_setup_validation(repo_root, paths)
    except Exception as exc:
        return emit_setup_result(
            args,
            False,
            "macs setup validate",
            {"message": f"Unable to validate repo-local setup: {exc}"},
            1,
        )
    return emit_setup_result(args, True, "macs setup validate", data, 0)


def handle_setup_dry_run(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths = build_paths(repo_root)
    data = {
        "dry_run": build_setup_dry_run(repo_root, paths),
    }
    return emit_setup_result(args, True, "macs setup dry-run", data, 0)


def handle_setup_guide(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths = build_paths(repo_root)
    data = {
        "guide": build_setup_guide(repo_root, paths),
    }
    return emit_setup_result(args, True, "macs setup guide", data, 0)


def load_repo_adapter_settings(paths) -> dict[str, object]:
    return load_adapter_settings(paths.adapter_settings_path)


def merge_adapter_settings(descriptor: dict[str, object], adapter_settings: dict[str, object]) -> dict[str, object]:
    updated = dict(descriptor)
    updated["settings"] = adapter_configuration(adapter_settings, str(descriptor["adapter_id"]))
    return updated


def emit_adapter_contract_human_readable(adapter: dict[str, object]) -> None:
    contract = adapter.get("contract")
    if not isinstance(contract, dict):
        return

    required_facts = contract.get("required_facts") or []
    if required_facts:
        print("Required Facts:")
        for fact in required_facts:
            print(f"- {fact}")

    required_operations = contract.get("required_operations") or []
    if required_operations:
        print("Required Operations:")
        for operation in required_operations:
            print(f"- {operation}")

    capability_model = contract.get("capability_model")
    if isinstance(capability_model, dict):
        print("Capability Model:")
        print(f"Declaration Field: {capability_model.get('declaration_field')}")
        print(f"Evidence Name: {capability_model.get('evidence_name')}")
        reference_workflows = capability_model.get("reference_workflow_classes") or []
        print(f"Reference Workflow Classes: {', '.join(reference_workflows) if reference_workflows else 'none'}")
        if capability_model.get("notes"):
            print(f"Capability Notes: {capability_model['notes']}")

    optional_enrichments = contract.get("optional_enrichments")
    if isinstance(optional_enrichments, dict):
        print("Optional Enrichments:")
        implemented = optional_enrichments.get("implemented") or []
        unsupported = optional_enrichments.get("unsupported") or []
        print(f"Implemented: {', '.join(implemented) if implemented else 'none'}")
        print(f"Unsupported: {', '.join(unsupported) if unsupported else 'none'}")

    degraded_mode = contract.get("degraded_mode_expectations")
    if isinstance(degraded_mode, dict):
        print("Degraded Mode:")
        print(f"Behavior: {degraded_mode.get('behavior')}")
        print(
            "Controller Authority Preserved: "
            f"{'yes' if degraded_mode.get('controller_authority_preserved') else 'no'}"
        )
        print(
            "Unsupported Features Must Be Declared: "
            f"{'yes' if degraded_mode.get('unsupported_features_must_be_declared') else 'no'}"
        )

    qualification_expectations = contract.get("qualification_expectations") or []
    if qualification_expectations:
        print("Qualification Steps:")
        for expectation in qualification_expectations:
            print(f"- {expectation}")

    validation_commands = contract.get("validation_commands") or []
    if validation_commands:
        print("Shared Validation Commands:")
        for command in validation_commands:
            print(f"- {command}")

    release_gate_criteria = contract.get("release_gate_criteria") or []
    if release_gate_criteria:
        print("Release-Gate Criteria:")
        for criterion in release_gate_criteria:
            print(f"- {criterion}")


def emit_adapter_validation_human_readable(validation: dict[str, object]) -> None:
    print("Validation Checks:")
    for check_name, result in validation.items():
        if isinstance(result, bool):
            print(f"- {check_name}: {'PASS' if result else 'FAIL'}")


def ensure_adapter_enabled_for_repo(paths, adapter_id: str) -> dict[str, object]:
    adapter_settings = load_repo_adapter_settings(paths)
    if not adapter_enabled(adapter_settings, adapter_id):
        raise RuntimeError(f"Adapter '{adapter_id}' is disabled by repo-local adapter settings")
    return adapter_settings


def handle_worker_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    decision_rights = None
    if args.verb in {"list", "inspect"}:
        classify_workers(paths.state_db, paths.events_ndjson)

    try:
        if args.verb == "list":
            workers = list_workers(paths.state_db)
            data = {"workers": workers}
        elif args.verb == "discover":
            discovered = discover_tmux_workers(
                repo_root,
                tmux_socket=getattr(args, "tmux_socket", None),
                tmux_session=getattr(args, "tmux_session", None),
            )
            workers = sync_discovered_workers(
                paths.state_db,
                paths.events_ndjson,
                discovered,
                scope_socket=getattr(args, "tmux_socket", None),
                scope_session=getattr(args, "tmux_session", None),
            )
            health_changes = classify_workers(paths.state_db, paths.events_ndjson)
            data = {"workers": workers, "discovered_count": len(discovered), "health_changes": health_changes}
        elif args.verb == "inspect":
            worker = inspect_worker_context(paths.state_db, args.worker_id)
            try:
                worker["adapter_evidence"] = get_adapter(worker["adapter_id"]).probe(worker)
            except RuntimeError as exc:
                worker["adapter_evidence"] = []
                worker["adapter_probe_warning"] = str(exc)
            worker["governance"] = governance_summary_for_worker(
                repo_root,
                worker,
                adapter_evidence=worker.get("adapter_evidence"),
            )
            if worker.get("adapter_probe_warning"):
                worker["governance"]["surface_version_pins"]["probe_error"] = worker["adapter_probe_warning"]
            if getattr(args, "open_pane", False):
                worker["pane_navigation"] = open_pane_target(repo_root, worker["controller_truth"]["pane_target"])
            data = {"worker": worker}
        elif args.verb == "register":
            get_adapter(args.adapter_id)
            ensure_adapter_enabled_for_repo(paths, args.adapter_id)
            worker = inspect_worker(paths.state_db, args.worker_id)
            registration_worker = dict(worker)
            registration_worker["adapter_id"] = args.adapter_id
            registration_governance = governance_summary_for_worker(
                repo_root,
                registration_worker,
                workflow_class=SURFACE_VERSION_PIN_SELECTOR_ANY,
                registration_scope=True,
            )
            adapter_probe_warning = None
            if registration_governance["surface_version_pins"].get("probe_required"):
                try:
                    adapter_evidence = get_adapter(args.adapter_id).probe(registration_worker)
                except RuntimeError as exc:
                    adapter_evidence = []
                    adapter_probe_warning = str(exc)
                registration_governance = governance_summary_for_worker(
                    repo_root,
                    registration_worker,
                    workflow_class=SURFACE_VERSION_PIN_SELECTOR_ANY,
                    adapter_evidence=adapter_evidence,
                    registration_scope=True,
                )
                if adapter_probe_warning is not None:
                    registration_governance["surface_version_pins"]["probe_error"] = adapter_probe_warning
            target_state = "quarantined" if not registration_governance["surface_version_pins"].get("eligible", True) else "ready"
            registered_worker = register_worker(
                paths.state_db,
                paths.events_ndjson,
                args.worker_id,
                args.adapter_id,
                target_state=target_state,
                event_payload={"governance": registration_governance},
            )
            registered_worker["governance"] = registration_governance
            if target_state == "quarantined":
                frozen = freeze_owned_active_tasks_for_worker(
                    paths.state_db,
                    paths.events_ndjson,
                    worker_id=args.worker_id,
                    worker_state=registered_worker["state"],
                    evidence_summary={
                        "worker_id": args.worker_id,
                        "surface_version_pins": registration_governance["surface_version_pins"],
                    },
                )
                message, next_action = worker_registration_block_message(
                    worker_id=args.worker_id,
                    governance=registration_governance,
                    policy_path=registration_governance.get("policy_path"),
                )
                return emit_result(
                    args,
                    False,
                    {
                        "message": message,
                        "next_action": next_action,
                        "worker": registered_worker,
                        "governance": registration_governance,
                        "controller_state_changed": True,
                        "frozen_tasks": [item["result"]["task"]["task_id"] for item in frozen],
                    },
                    4,
                )
            data = {"worker": registered_worker, "governance": registration_governance}
        elif args.verb == "enable":
            data = {"worker": set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "ready")}
        elif args.verb == "disable":
            decision_rights = evaluate_decision_rights("worker.disable")
            worker = set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "unavailable")
            frozen = freeze_owned_active_tasks_for_worker(
                paths.state_db,
                paths.events_ndjson,
                worker_id=args.worker_id,
                worker_state=worker["state"],
                evidence_summary={"worker_id": args.worker_id, "next_state": worker["state"]},
            )
            data = {
                "worker": worker,
                "frozen_tasks": [item["result"]["task"]["task_id"] for item in frozen],
                "decision_rights": decision_rights,
            }
        elif args.verb == "quarantine":
            decision_rights = evaluate_decision_rights("worker.quarantine")
            worker = set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "quarantined")
            frozen = freeze_owned_active_tasks_for_worker(
                paths.state_db,
                paths.events_ndjson,
                worker_id=args.worker_id,
                worker_state=worker["state"],
                evidence_summary={"worker_id": args.worker_id, "next_state": worker["state"]},
            )
            data = {
                "worker": worker,
                "frozen_tasks": [item["result"]["task"]["task_id"] for item in frozen],
                "decision_rights": decision_rights,
            }
        else:
            raise SystemExit("unsupported worker command")
    except WorkerNotFoundError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    except RuntimeError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)

    if args.json_output:
        if args.verb == "inspect":
            warnings = worker_inspect_warnings(data["worker"])
            payload = {
                "ok": True,
                "command": "macs worker inspect",
                "timestamp": action_timestamp(),
                "warnings": warnings,
                "errors": [],
                "worker": data["worker"],
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        payload = {"ok": True, "command": f"macs worker {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.verb in {"list", "discover"}:
        print(f"Workers: {len(data['workers'])}")
        for worker in data["workers"]:
            print(
                f"{worker['worker_id']}  {worker['runtime_type']}  {worker['state']}  "
                f"{worker['tmux_session']}:{worker['tmux_pane']}"
            )
    else:
        emit_worker_inspect_human_readable(data["worker"])
        if isinstance(data.get("decision_rights"), dict):
            print(f"Decision Rights: {data['decision_rights']['decision_class']}")
            confirmation = decision_rights_confirmation_label(data["decision_rights"])
            if confirmation is not None:
                print(f"Confirmation: {confirmation}")
    return 0


def handle_adapter_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    adapter_settings = load_repo_adapter_settings(paths)

    try:
        if args.verb == "list":
            data = {
                "adapters": [
                    merge_adapter_settings(adapter, adapter_settings)
                    for adapter in list_adapters()
                ]
            }
        elif args.verb == "inspect":
            adapter = get_adapter(args.adapter_id)
            descriptor = merge_adapter_settings(adapter.descriptor(), adapter_settings)
            data = {
                "adapter": descriptor,
                "governance": adapter_governance_summary(repo_root, descriptor),
            }
        elif args.verb == "validate":
            adapter = get_adapter(args.adapter_id)
            descriptor = merge_adapter_settings(adapter.descriptor(), adapter_settings)
            data = {
                "adapter": descriptor,
                "validation": adapter.validate_contract(),
                "governance": adapter_governance_summary(repo_root, descriptor),
            }
        elif args.verb == "probe":
            if getattr(args, "worker_id", None):
                worker = inspect_worker(paths.state_db, args.worker_id)
                adapter = get_adapter(worker["adapter_id"])
                data = {"worker": worker, "evidence": adapter.probe(worker)}
            else:
                adapter = get_adapter(args.adapter_id)
                data = {"adapter": merge_adapter_settings(adapter.descriptor(), adapter_settings)}
        else:
            raise SystemExit("unsupported adapter command")
    except (RuntimeError, WorkerNotFoundError) as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)

    if args.json_output:
        payload = {"ok": True, "command": f"macs adapter {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.verb == "list":
        print(f"Adapters: {len(data['adapters'])}")
        for adapter in data["adapters"]:
            enabled_state = "enabled" if adapter.get("settings", {}).get("enabled", True) else "disabled"
            print(
                f"{adapter['adapter_id']}  {adapter['runtime_type']}  "
                f"{adapter['qualification_status']}  {enabled_state}"
            )
    elif args.verb == "probe" and "evidence" in data:
        print(f"Evidence items: {len(data['evidence'])}")
        for item in data["evidence"]:
            print(f"{item['name']}  {item['kind']}  freshness={item['freshness_seconds']}s")
    else:
        adapter = data.get("adapter") or data["worker"]
        print(f"Adapter: {adapter['adapter_id']}")
        print(f"Runtime: {adapter['runtime_type']}")
        if "qualification_status" in adapter:
            print(f"Qualification: {adapter['qualification_status']}")
        if isinstance(adapter.get("settings"), dict):
            print(f"Configured Enabled: {adapter['settings']['enabled']}")
            print(f"Config Ref: {adapter['settings']['config_ref']}")
            if adapter["settings"].get("notes"):
                print(f"Config Notes: {adapter['settings']['notes']}")
        emit_adapter_contract_human_readable(adapter)
        if args.verb == "validate" and isinstance(data.get("validation"), dict):
            emit_adapter_validation_human_readable(data["validation"])
        governance = data.get("governance")
        if isinstance(governance, dict):
            print(f"Governance Policy: {governance.get('policy_version')}")
            print(f"Active operating profile: {governance.get('operating_profile', 'unknown')}")
            snapshot = governance.get("active_snapshot") or {}
            print(f"Governance snapshot: {format_governance_snapshot_reference(snapshot)}")
            if snapshot.get("traceability_status") == "stale_vs_live_policy":
                for line in surface_version_pin_summary_lines(
                    snapshot.get("surface_version_pins"),
                    label="Snapshot-captured surface version pins",
                ):
                    print(line)
                for line in secret_scope_summary_lines(
                    snapshot.get("secret_scopes"),
                    label="Snapshot-captured secret scopes",
                ):
                    print(line)
            declared = governance.get("declared_surfaces") or []
            if declared:
                print("Declared Governed Surfaces:")
                for surface in declared:
                    status = "allowlisted" if surface.get("allowlisted") else "blocked"
                    if surface.get("requires_secret"):
                        status += " secret-required"
                    if surface.get("pinned_adapters"):
                        status += f" pinned={','.join(surface['pinned_adapters'])}"
                    version_pins = surface.get("applicable_version_pins") or []
                    if version_pins:
                        status += f" version-pin={'; '.join(format_surface_version_pin(pin) for pin in version_pins)}"
                    secret_scopes = surface.get("applicable_secret_scopes") or []
                    if secret_scopes:
                        status += f" secret-scope={'; '.join(format_secret_scope(scope) for scope in secret_scopes)}"
                    print(f"- {surface['surface_id']} ({status})")
            else:
                print("Declared Governed Surfaces: none")
            for line in surface_version_pin_summary_lines(governance.get("surface_version_pins")):
                print(line)
            for line in secret_scope_summary_lines(governance.get("secret_scopes")):
                print(line)
    return 0


def handle_task_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    decision_rights = None
    affected_refs = {"task_id": getattr(args, "task_id", None)} if getattr(args, "task_id", None) else None

    try:
        if args.verb == "list":
            data = {"tasks": list_tasks(paths.state_db)}
        elif args.verb == "create":
            controller_defaults = load_controller_defaults(paths.controller_defaults_path)
            task_defaults = controller_defaults.get("task", {})
            action = create_task_record(
                paths.state_db,
                paths.events_ndjson,
                summary=args.summary,
                workflow_class=str(args.workflow_class or task_defaults.get("default_workflow_class", "implementation")),
                required_capabilities=args.required_capabilities,
                protected_surfaces=args.protected_surfaces,
                priority=str(task_defaults.get("default_priority", "normal")),
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "inspect":
            classify_workers(paths.state_db, paths.events_ndjson)
            task = inspect_task_context(paths.state_db, args.task_id)
            current_owner = task["controller_truth"].get("current_owner")
            if isinstance(current_owner, dict):
                worker = inspect_worker(paths.state_db, str(current_owner["worker_id"]))
                task["governance"] = governance_summary_for_worker(
                    repo_root,
                    worker,
                    workflow_class=str(task["workflow_class"]),
                    adapter_evidence=task.get("adapter_evidence"),
                    persist_sanitized=False,
                )
                if task.get("adapter_probe_warning"):
                    task["governance"]["surface_version_pins"]["probe_error"] = task["adapter_probe_warning"]
            task["governance_evidence"] = summarize_governance_evidence(
                paths.state_db,
                task=task,
                governance=task.get("governance"),
            )
            if getattr(args, "open_pane", False):
                task["pane_navigation"] = open_pane_target(repo_root, task["controller_truth"]["pane_target"])
            data = {"task": task}
        elif args.verb == "assign":
            decision_rights = evaluate_decision_rights("task.assign")
            action = assign_task(
                repo_root,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                explicit_worker_id=getattr(args, "worker_id", None),
                workflow_class=getattr(args, "workflow_class", None),
            )
            action["result"] = action_result_with_decision_rights(
                action["result"],
                decision_rights,
                controller_state_changed=True,
                affected_refs=affected_refs,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "close":
            action = close_task(
                repo_root,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "checkpoint":
            action = checkpoint_task(
                repo_root,
                paths.checkpoints_dir,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                target_action=args.target_action,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "archive":
            action = archive_task(
                repo_root,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "pause":
            decision_rights = evaluate_decision_rights("task.pause", confirmed=getattr(args, "confirm", False))
            if not decision_rights["allowed"]:
                return emit_task_action_error(
                    args,
                    args.verb,
                    message=str(decision_rights["policy_message"]),
                    code=str(decision_rights["error_code"]),
                    exit_code=int(decision_rights["error_exit_code"]),
                    result=decision_rights_error_result(
                        decision_rights,
                        affected_refs=affected_refs,
                        next_action=task_confirm_next_action(args),
                    ),
                )
            action = pause_task(
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                rationale=getattr(args, "rationale", None),
            )
            action["result"] = action_result_with_decision_rights(
                action["result"],
                decision_rights,
                affected_refs=affected_refs,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "resume":
            decision_rights = evaluate_decision_rights("task.resume", confirmed=getattr(args, "confirm", False))
            if not decision_rights["allowed"]:
                return emit_task_action_error(
                    args,
                    args.verb,
                    message=str(decision_rights["policy_message"]),
                    code=str(decision_rights["error_code"]),
                    exit_code=int(decision_rights["error_exit_code"]),
                    result=decision_rights_error_result(
                        decision_rights,
                        affected_refs=affected_refs,
                        next_action=task_confirm_next_action(args),
                    ),
                )
            action = resume_task(
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
            )
            action["result"] = action_result_with_decision_rights(
                action["result"],
                decision_rights,
                affected_refs=affected_refs,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "reroute":
            decision_rights = evaluate_decision_rights("task.reroute", confirmed=getattr(args, "confirm", False))
            if not decision_rights["allowed"]:
                return emit_task_action_error(
                    args,
                    args.verb,
                    message=str(decision_rights["policy_message"]),
                    code=str(decision_rights["error_code"]),
                    exit_code=int(decision_rights["error_exit_code"]),
                    result=decision_rights_error_result(
                        decision_rights,
                        affected_refs=affected_refs,
                        next_action=task_confirm_next_action(args),
                    ),
                )
            action = reroute_task(
                repo_root,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                explicit_worker_id=getattr(args, "worker_id", None),
                workflow_class=getattr(args, "workflow_class", None),
                rationale=getattr(args, "rationale", None),
            )
            action["result"] = action_result_with_decision_rights(
                action["result"],
                decision_rights,
                affected_refs=affected_refs,
            )
            return emit_task_action_result(args, args.verb, action)
        elif args.verb == "abort":
            decision_rights = evaluate_decision_rights("task.abort", confirmed=getattr(args, "confirm", False))
            return emit_task_action_error(
                args,
                args.verb,
                message=str(decision_rights["policy_message"]),
                code=str(decision_rights["error_code"]),
                exit_code=int(decision_rights["error_exit_code"]),
                result=decision_rights_error_result(decision_rights, affected_refs=affected_refs),
            )
        else:
            raise SystemExit("unsupported task command")
    except TaskActionError as exc:
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code=exc.code,
            exit_code=exc.exit_code,
            result=action_result_with_decision_rights(exc.result, decision_rights, affected_refs=affected_refs),
            event=exc.event,
        )
    except TaskNotFoundError as exc:
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code="not_found",
            exit_code=3,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )
    except WorkerNotFoundError as exc:
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code="not_found",
            exit_code=3,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )
    except (LockConflictError, InvariantViolationError) as exc:
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code="conflict",
            exit_code=4,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )
    except RoutingError as exc:
        if "Assignments are blocked pending startup recovery reconciliation" in str(exc):
            return emit_task_action_error(
                args,
                args.verb,
                message=str(exc),
                code="degraded_precondition",
                exit_code=5,
                result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
            )
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code="policy_blocked",
            exit_code=4,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )
    except RuntimeError as exc:
        return emit_task_action_error(
            args,
            args.verb,
            message=str(exc),
            code="internal_error",
            exit_code=1,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )

    if args.json_output:
        if args.verb == "inspect":
            warnings = task_inspect_warnings(data["task"])
            payload = {
                "ok": True,
                "command": "macs task inspect",
                "timestamp": action_timestamp(),
                "warnings": warnings,
                "errors": [],
                "task": data["task"],
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        payload = {"ok": True, "command": f"macs task {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.verb == "list":
        print(f"Tasks: {len(data['tasks'])}")
        for task in data["tasks"]:
            print(f"{task['task_id']}  {task['workflow_class']}  {task['state']}  owner={task['current_worker_id']}")
    else:
        emit_task_inspect_human_readable(data["task"])
    return 0


def handle_lock_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    if args.verb == "list":
        data = {"locks": list_locks(paths.state_db)}
        if args.json_output:
            payload = {"ok": True, "command": f"macs lock {args.verb}", "data": data, "error": None}
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(f"Locks: {len(data['locks'])}")
        for lock in data["locks"]:
            print(f"{lock['lock_id']}  {lock['surface_ref']}  {lock['state']}  task={lock['task_id']}")
        return 0

    if args.verb == "inspect":
        try:
            lock = inspect_lock(paths.state_db, args.lock_id)
        except RuntimeError as exc:
            return emit_lock_action_error(args, args.verb, message=str(exc), code="not_found", exit_code=3)
        if args.json_output:
            payload = {"ok": True, "command": "macs lock inspect", "data": {"lock": lock}, "error": None}
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0
        print(f"Lock: {lock['lock_id']}")
        print(f"Surface: {lock['surface_ref']}")
        print(f"State: {lock['state']}")
        print(f"Task: {lock['task_id']}")
        print(f"Lease: {lock['lease_id']}")
        return 0

    decision_rights = evaluate_decision_rights(f"lock.{args.verb}", confirmed=getattr(args, "confirm", False))
    return emit_lock_action_error(
        args,
        args.verb,
        message=str(decision_rights["policy_message"]),
        code=str(decision_rights["error_code"]),
        exit_code=int(decision_rights["error_exit_code"]),
        result=decision_rights_error_result(
            decision_rights,
            affected_refs={"lock_id": args.lock_id},
        ),
    )


def handle_lease_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    try:
        if args.verb == "inspect":
            classify_workers(paths.state_db, paths.events_ndjson)
            lease = inspect_lease(paths.state_db, args.lease_id)
            task = inspect_task(paths.state_db, lease["task_id"])
            worker = inspect_worker(paths.state_db, lease["worker_id"])
            assignments_blocked = metadata_value(paths.state_db, "assignments_blocked") == "1"
            recent_event_refs = list_aggregate_events(paths.state_db, args.lease_id)
            data = {
                "lease": lease,
                "recent_event_refs": recent_event_refs,
                "decision_event": decision_event_for_ref(
                    paths.state_db,
                    recent_event_refs[0] if recent_event_refs else None,
                ),
                "blocking_condition": intervention_blocking_condition(
                    task_state=task["state"],
                    lease_state=lease["state"],
                    owner_state=worker["state"],
                    assignments_blocked=assignments_blocked,
                ),
                "next_action": intervention_next_action(
                    task_id=task["task_id"],
                    task_state=task["state"],
                    lease_state=lease["state"],
                    owner_state=worker["state"],
                    assignments_blocked=assignments_blocked,
                ),
            }
        else:
            data = {"leases": list_lease_history(paths.state_db, task_id=getattr(args, "task_id", None), worker_id=getattr(args, "worker_id", None))}
    except (ObjectNotFoundError, RuntimeError) as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    if args.json_output:
        payload = {"ok": True, "command": f"macs lease {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.verb == "inspect":
        runtime_intervention = lease_inspect_runtime_intervention(paths.state_db, data["lease"])
        emit_lease_inspect_human_readable(
            data["lease"],
            runtime_intervention,
            data.get("blocking_condition"),
            data.get("next_action"),
            data.get("decision_event"),
            data.get("recent_event_refs"),
        )
    else:
        print(f"Leases: {len(data['leases'])}")
        for lease in data["leases"]:
            latest_event_ref = lease.get("latest_event_ref") or {}
            decision_event = lease.get("decision_event") or {}
            line = f"{lease['lease_id']}  {lease['task_id']}  {lease['worker_id']}  {lease['state']}"
            if latest_event_ref.get("event_id"):
                line += f"  latest={latest_event_ref['event_id']}"
            if latest_event_ref.get("causation_id"):
                line += f"  cause={latest_event_ref['causation_id']}"
            if decision_event.get("actor_id"):
                line += f"  actor={decision_event['actor_id']}"
            if decision_event.get("intervention_rationale"):
                line += f"  rationale={decision_event['intervention_rationale']}"
            print(line)
    return 0


def handle_event_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    try:
        if args.verb == "list":
            data = {"events": list_events(paths.state_db)}
        else:
            event = inspect_event(paths.state_db, args.event_id)
            data = {"event": event}
            checkpoint = checkpoint_for_ref(paths.state_db, event)
            if checkpoint is not None:
                data["checkpoint"] = checkpoint
            decision_event = decision_event_for_ref(paths.state_db, event)
            if decision_event is not None:
                data["decision_event"] = decision_event
            governance_evidence = summarize_governance_evidence(paths.state_db, event=event)
            if governance_evidence is not None:
                data["governance_evidence"] = governance_evidence
    except ObjectNotFoundError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    if args.json_output:
        payload = {"ok": True, "command": f"macs event {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.verb == "list":
        print(f"Events: {len(data['events'])}")
        for event in data["events"]:
            affected_refs = format_affected_refs(event.get("affected_refs"))
            print(
                f"{event['event_id']}  {event['event_type']}  {event['aggregate_type']}:{event['aggregate_id']}  "
                f"actor={event['actor_id']}"
                + (f"  cause={event['causation_id']}" if event.get("causation_id") else "")
                + (
                    f"  rationale={event['intervention_rationale']}"
                    if event.get("intervention_rationale")
                    else ""
                )
                + (
                    f"  redaction={event['redaction_level']}"
                    if event.get("redaction_level") and event["redaction_level"] != "none"
                    else ""
                )
                + (f"  {affected_refs}" if affected_refs else "")
            )
    else:
        event = data["event"]
        render_context = terminal_render_context()
        print_key_value("Event", event["event_id"], render_context)
        print_key_value("Type", event["event_type"], render_context)
        print_key_value("Actor", f"{event['actor_type']} {event['actor_id']}", render_context)
        print_key_value("Timestamp", event["timestamp"], render_context)
        print_key_value("Correlation", event["correlation_id"], render_context)
        print_key_value("Causation", event.get("causation_id") or "none", render_context)
        print_key_value("Redaction Level", event.get("redaction_level") or "none", render_context)
        if event.get("intervention_rationale"):
            print_key_value("Intervention Rationale", event["intervention_rationale"], render_context)
        affected_refs = format_affected_refs(event.get("affected_refs"))
        if affected_refs:
            print_key_value("Affected Refs", affected_refs, render_context)
        checkpoint = data.get("checkpoint")
        if isinstance(checkpoint, dict):
            print_key_value("Checkpoint", checkpoint["checkpoint_id"], render_context)
            print_key_value("Target Action", checkpoint["target_action"], render_context)
            print_key_value("Captured At", checkpoint["captured_at"], render_context)
            baseline = format_checkpoint_baseline_summary(checkpoint.get("baseline_fingerprint"))
            if baseline:
                print_key_value("Baseline Repo", baseline, render_context)
            evidence_refs = format_evidence_refs(checkpoint.get("evidence_refs"))
            if evidence_refs:
                print_key_value("Evidence Refs", evidence_refs, render_context)
        decision_event = data.get("decision_event")
        if isinstance(decision_event, dict):
            print_key_value("Decision Event", decision_event["event_id"], render_context)
            print_key_value("Decision Actor", decision_event["actor_id"], render_context)
            if decision_event.get("intervention_rationale"):
                print_key_value("Intervention Rationale", decision_event["intervention_rationale"], render_context)
        for line in audit_content_lines(event):
            print(line)
        secret_resolution = (event.get("payload") or {}).get("secret_resolution")
        for line in secret_resolution_lines(secret_resolution):
            print(line)
        for line in governance_evidence_lines(data.get("governance_evidence")):
            print(line)
    return 0


def handle_overview_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    changes = classify_workers(paths.state_db, paths.events_ndjson)
    data = {"overview": build_overview(paths.state_db)}
    if changes:
        data["health_changes"] = changes
    if args.json_output:
        payload = {"ok": True, "command": f"macs overview {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    overview = data["overview"]
    print(f"Active alerts: {len(overview['active_alerts'])}")
    print(f"Workers: {overview['worker_summary']}")
    print(f"Tasks: {overview['task_summary']}")
    print(f"Locks held/reserved: {overview['locks']['held_or_reserved']}")
    if overview["active_alerts"]:
        print("Alerts:")
        for alert in overview["active_alerts"]:
            if alert["kind"] == "worker_state":
                print(f"{alert['kind']}  {alert['worker_id']}  {alert['state']}")
            elif alert["kind"] == "task_hold":
                recovery_suffix = ""
                if alert.get("recovery_run_state"):
                    recovery_suffix = f"  recovery={alert['recovery_run_state']}"
                print(
                    f"{alert['kind']}  {alert['task_id']}  lease={alert['lease_state']}  "
                    f"basis={alert['intervention_reason']}  blocking={alert['blocking_condition']}  "
                    f"next={alert['next_action']}{recovery_suffix}"
                )
    held_tasks = [task for task in overview["active_tasks"] if task["state"] == "intervention_hold"]
    if held_tasks:
        print("Held Tasks:")
        for task in held_tasks:
            recovery_suffix = ""
            if task.get("recovery_run_state"):
                recovery_suffix = f"  recovery={task['recovery_run_state']}"
            print(
                f"{task['task_id']}  {task['state']}  lease={task['lease_state']}  "
                f"basis={task['intervention_reason']}  blocking={task['blocking_condition']}  "
                f"next={task['next_action']}{recovery_suffix}"
            )
    recovery_tasks = [
        task
        for task in overview["active_tasks"]
        if task["state"] == "reconciliation" and task.get("recovery_run_state")
    ]
    if recovery_tasks:
        print("Recovery Tasks:")
        for task in recovery_tasks:
            recovery_suffix = f"  recovery={task['recovery_run_state']}"
            lease_state = task["lease_state"] or "none"
            print(
                f"{task['task_id']}  {task['state']}  lease={lease_state}  "
                f"blocking={task['blocking_condition']}  next={task['next_action']}{recovery_suffix}"
            )
    return 0


def handle_recovery_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _, _ = ensure_orchestration_store(repo_root)
    decision_rights = None
    affected_refs = {"task_id": getattr(args, "task_id", None)} if getattr(args, "task_id", None) else None
    try:
        if args.verb == "inspect":
            recovery = inspect_recovery_context(paths.state_db, task_id=args.task_id)
            if args.json_output:
                payload = {
                    "ok": True,
                    "command": "macs recovery inspect",
                    "timestamp": action_timestamp(),
                    "warnings": [],
                    "errors": [],
                    "data": {"recovery": recovery},
                }
                print(json.dumps(payload, indent=2, sort_keys=True))
                return 0

            run = recovery.get("recovery_run") or {}
            anomaly = recovery.get("anomaly_summary") or {}
            current = recovery.get("current_state") or {}
            proposed = recovery.get("proposed_state") or {}
            decision = recovery.get("latest_intervention_decision") or {}
            print(f"Recovery Run: {run.get('recovery_run_id', 'none')}")
            print(f"State: {run.get('state', 'none')}")
            print(f"Anomaly Summary: {anomaly.get('kind', 'unknown')}")
            if recovery.get("blocking_condition"):
                print(f"Blocking Condition: {recovery['blocking_condition']}")
            print(f"Task: {current.get('task_id', 'unknown')}")
            print(f"Task State: {current.get('task_state', 'unknown')}")
            print(f"Current Worker: {current.get('current_worker_id', 'none')}")
            print(f"Current Lease: {current.get('current_lease_id', 'none')}")
            if decision.get("event_id"):
                print(f"Decision Event: {decision['event_id']}")
            if decision.get("actor_id"):
                print(f"Decision Actor: {decision['actor_id']}")
            if decision.get("intervention_rationale"):
                print(f"Intervention Rationale: {decision['intervention_rationale']}")
            if proposed.get("selected_worker_id"):
                print(f"Proposed Worker: {proposed['selected_worker_id']}")
            if proposed.get("workflow_class"):
                print(f"Proposed Workflow Class: {proposed['workflow_class']}")
            recent_event_refs = recovery.get("recent_event_refs") or []
            if recent_event_refs:
                print("Recent Events:")
                for event in recent_event_refs:
                    print(f"- {render_event_ref_line(event)}")
            print("Allowed Next Actions:")
            for action in recovery.get("allowed_next_actions", []):
                print(f"- {action}")
            return 0

        if args.verb == "retry":
            decision_rights = evaluate_decision_rights("recovery.retry", confirmed=getattr(args, "confirm", False))
            if not decision_rights["allowed"]:
                return emit_recovery_action_error(
                    args,
                    args.verb,
                    message=str(decision_rights["policy_message"]),
                    code=str(decision_rights["error_code"]),
                    exit_code=int(decision_rights["error_exit_code"]),
                    result=decision_rights_error_result(
                        decision_rights,
                        affected_refs=affected_refs,
                        next_action=recovery_confirm_next_action(args),
                    ),
                )
            action = retry_task_recovery(
                repo_root,
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                rationale=getattr(args, "rationale", None),
            )
        elif args.verb == "reconcile":
            decision_rights = evaluate_decision_rights(
                "recovery.reconcile",
                confirmed=getattr(args, "confirm", False),
            )
            if not decision_rights["allowed"]:
                return emit_recovery_action_error(
                    args,
                    args.verb,
                    message=str(decision_rights["policy_message"]),
                    code=str(decision_rights["error_code"]),
                    exit_code=int(decision_rights["error_exit_code"]),
                    result=decision_rights_error_result(
                        decision_rights,
                        affected_refs=affected_refs,
                        next_action=recovery_confirm_next_action(args),
                    ),
                )
            action = reconcile_task_recovery(
                paths.state_db,
                paths.events_ndjson,
                task_id=args.task_id,
                rationale=getattr(args, "rationale", None),
            )
        else:
            raise RuntimeError(f"Recovery action '{args.verb}' is not implemented yet")
    except TaskActionError as exc:
        return emit_recovery_action_error(
            args,
            args.verb,
            message=str(exc),
            code=exc.code,
            exit_code=exc.exit_code,
            result=action_result_with_decision_rights(exc.result, decision_rights, affected_refs=affected_refs),
            event=exc.event,
        )
    except RuntimeError as exc:
        return emit_recovery_action_error(
            args,
            args.verb,
            message=str(exc),
            code="not_found" if args.verb == "inspect" else "unsupported",
            exit_code=3 if args.verb == "inspect" else 5,
            result=action_result_with_decision_rights({}, decision_rights, affected_refs=affected_refs),
        )

    if decision_rights is not None:
        action["result"] = action_result_with_decision_rights(action["result"], decision_rights, affected_refs=affected_refs)
    return emit_recovery_action_result(args, args.verb, action)


def metadata_value(state_db: Path, key: str) -> str | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row["value"]


def main() -> int:
    args = parse_args()
    if args.family == "setup" and args.verb == "init":
        return handle_setup_init(args)
    if args.family == "setup" and args.verb == "check":
        return handle_setup_check(args)
    if args.family == "setup" and args.verb == "validate":
        return handle_setup_validate(args)
    if args.family == "setup" and args.verb == "dry-run":
        return handle_setup_dry_run(args)
    if args.family == "setup" and args.verb == "guide":
        return handle_setup_guide(args)
    if args.family == "worker":
        return handle_worker_command(args)
    if args.family == "adapter":
        return handle_adapter_command(args)
    if args.family == "task":
        return handle_task_command(args)
    if args.family == "lock":
        return handle_lock_command(args)
    if args.family == "lease":
        return handle_lease_command(args)
    if args.family == "event":
        return handle_event_command(args)
    if args.family == "overview":
        return handle_overview_command(args)
    if args.family == "recovery":
        return handle_recovery_command(args)
    raise SystemExit("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
