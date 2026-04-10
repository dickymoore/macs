#!/usr/bin/env python3
"""MACS orchestration CLI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.orchestration.session import (
    ControllerSessionLock,
    SessionLockHeldError,
    build_lock_metadata,
    ensure_orchestration_store,
    render_lock_error,
    setup_orchestration,
)
from tools.orchestration.adapters.registry import get_adapter, list_adapters
from tools.orchestration.history import (
    ObjectNotFoundError,
    inspect_event,
    inspect_lease,
    list_events,
    list_lease_history,
)
from tools.orchestration.health import classify_workers
from tools.orchestration.invariants import InvariantViolationError
from tools.orchestration.locks import LockConflictError, list_locks
from tools.orchestration.overview import build_overview
from tools.orchestration.workers import (
    WorkerNotFoundError,
    discover_tmux_workers,
    inspect_worker,
    list_workers,
    register_worker,
    set_worker_state,
    sync_discovered_workers,
)
from tools.orchestration.routing import RoutingError
from tools.orchestration.tasks import TaskNotFoundError, assign_task, create_task_record, inspect_task, list_tasks


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
    task_create_parser.add_argument("--workflow-class", required=True, dest="workflow_class", help="workflow class")
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

    task_inspect_parser = task_subparsers.add_parser("inspect", help="inspect a task")
    task_inspect_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)
    task_inspect_parser.add_argument("--task", required=True, dest="task_id", help="task id")

    lock_list_parser = lock_subparsers.add_parser("list", help="list locks")
    lock_list_parser.add_argument("--json", action="store_true", dest="json_output", help=argparse.SUPPRESS)

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
    return parser.parse_args()


def emit_result(args: argparse.Namespace, ok: bool, data: dict[str, object], exit_code: int) -> int:
    if args.json_output:
        payload = {
            "ok": ok,
            "command": "macs setup init",
            "data": data if ok else {},
            "error": None if ok else data,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if ok:
            print("Initialized repo-local orchestration layout.")
            print(f"Orchestration dir: {data['orchestration_dir']}")
            print(f"Controller lock: {data['controller_lock']}")
            print(f"State DB ({data['state_db_status']}): {data['state_db']}")
            print(f"Events export ({data['events_ndjson_status']}): {data['events_ndjson']}")
            print(
                "Startup summary: "
                f"{data['startup_summary']['restored_entities']['tasks']} tasks restored, "
                f"{len(data['startup_summary']['unresolved_anomalies']['tasks_pending_reconciliation'])} pending reconciliation, "
                f"assignments blocked={data['startup_summary']['assignments_blocked']}"
            )
            if data.get("holding_lock"):
                print("Controller session lock acquired.")
        else:
            print(data["message"], file=sys.stderr)
    return exit_code


def handle_setup_init(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, store_result, recovery_summary = setup_orchestration(repo_root)
    lock = ControllerSessionLock(paths.controller_lock)
    data = {
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "controller_lock": str(paths.controller_lock),
        "state_db": str(paths.state_db),
        "events_ndjson": str(paths.events_ndjson),
        "state_db_status": "created" if store_result.state_db_created else "verified",
        "events_ndjson_status": "created" if store_result.events_ndjson_created else "verified",
        "holding_lock": False,
        "startup_summary": recovery_summary.as_dict(),
    }

    if not args.exec_cmd:
        return emit_result(args, True, data, 0)

    cmd = list(args.exec_cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    try:
        lock.acquire(build_lock_metadata(repo_root))
    except SessionLockHeldError as exc:
        message = render_lock_error(exc.info)
        return emit_result(args, False, {"message": message}, 2)

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
        return emit_result(
            args,
            False,
            {"message": f"Unable to exec command: {cmd[0]}"},
            127,
        )


def handle_worker_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)
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
            workers = sync_discovered_workers(paths.state_db, paths.events_ndjson, discovered)
            data = {"workers": workers, "discovered_count": len(discovered)}
        elif args.verb == "inspect":
            data = {"worker": inspect_worker(paths.state_db, args.worker_id)}
        elif args.verb == "register":
            data = {"worker": register_worker(paths.state_db, paths.events_ndjson, args.worker_id, args.adapter_id)}
        elif args.verb == "enable":
            data = {"worker": set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "ready")}
        elif args.verb == "disable":
            data = {"worker": set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "unavailable")}
        elif args.verb == "quarantine":
            data = {"worker": set_worker_state(paths.state_db, paths.events_ndjson, args.worker_id, "quarantined")}
        else:
            raise SystemExit("unsupported worker command")
    except WorkerNotFoundError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    except RuntimeError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)

    if args.json_output:
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
        worker = data["worker"]
        print(f"Worker: {worker['worker_id']}")
        print(f"Runtime: {worker['runtime_type']}")
        print(f"State: {worker['state']}")
        print(f"Adapter: {worker['adapter_id']}")
        print(f"tmux: {worker['tmux_session']} {worker['tmux_pane']}")
    return 0


def handle_adapter_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)

    try:
        if args.verb == "list":
            data = {"adapters": list_adapters()}
        elif args.verb == "inspect":
            data = {"adapter": get_adapter(args.adapter_id).descriptor()}
        elif args.verb == "validate":
            adapter = get_adapter(args.adapter_id)
            data = {"adapter": adapter.descriptor(), "validation": adapter.validate_contract()}
        elif args.verb == "probe":
            if getattr(args, "worker_id", None):
                worker = inspect_worker(paths.state_db, args.worker_id)
                adapter = get_adapter(worker["adapter_id"])
                data = {"worker": worker, "evidence": adapter.probe(worker)}
            else:
                adapter = get_adapter(args.adapter_id)
                data = {"adapter": adapter.descriptor()}
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
            print(f"{adapter['adapter_id']}  {adapter['runtime_type']}  {adapter['qualification_status']}")
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
    return 0


def handle_task_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)

    try:
        if args.verb == "list":
            data = {"tasks": list_tasks(paths.state_db)}
        elif args.verb == "create":
            data = {
                "task": create_task_record(
                    paths.state_db,
                    paths.events_ndjson,
                    summary=args.summary,
                    workflow_class=args.workflow_class,
                    required_capabilities=args.required_capabilities,
                    protected_surfaces=args.protected_surfaces,
                )
            }
        elif args.verb == "inspect":
            data = {"task": inspect_task(paths.state_db, args.task_id)}
        elif args.verb == "assign":
            data = {
                "result": assign_task(
                    repo_root,
                    paths.state_db,
                    paths.events_ndjson,
                    task_id=args.task_id,
                    explicit_worker_id=getattr(args, "worker_id", None),
                )
            }
        else:
            raise SystemExit("unsupported task command")
    except (TaskNotFoundError, RoutingError, LockConflictError, InvariantViolationError, RuntimeError) as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)

    if args.json_output:
        payload = {"ok": True, "command": f"macs task {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.verb == "list":
        print(f"Tasks: {len(data['tasks'])}")
        for task in data["tasks"]:
            print(f"{task['task_id']}  {task['workflow_class']}  {task['state']}  owner={task['current_worker_id']}")
    elif args.verb == "assign":
        result = data["result"]
        print(f"Task: {result['task']['task_id']}")
        print(f"State: {result['task']['state']}")
        print(f"Worker: {result['selected_worker_id']}")
        print(f"Lease: {result['lease_id']}")
    else:
        task = data["task"]
        print(f"Task: {task['task_id']}")
        print(f"Summary: {task['summary']}")
        print(f"State: {task['state']}")
        print(f"Owner: {task['current_worker_id']}")
    return 0


def handle_lock_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)
    data = {"locks": list_locks(paths.state_db)}
    if args.json_output:
        payload = {"ok": True, "command": f"macs lock {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"Locks: {len(data['locks'])}")
    for lock in data["locks"]:
        print(f"{lock['lock_id']}  {lock['surface_ref']}  {lock['state']}  task={lock['task_id']}")
    return 0


def handle_lease_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)
    try:
        if args.verb == "inspect":
            data = {"lease": inspect_lease(paths.state_db, args.lease_id)}
        else:
            data = {"leases": list_lease_history(paths.state_db, task_id=getattr(args, "task_id", None), worker_id=getattr(args, "worker_id", None))}
    except (ObjectNotFoundError, RuntimeError) as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    if args.json_output:
        payload = {"ok": True, "command": f"macs lease {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.verb == "inspect":
        print(f"Lease: {data['lease']['lease_id']}")
        print(f"Task: {data['lease']['task_id']}")
        print(f"Worker: {data['lease']['worker_id']}")
        print(f"State: {data['lease']['state']}")
    else:
        print(f"Leases: {len(data['leases'])}")
        for lease in data["leases"]:
            print(f"{lease['lease_id']}  {lease['task_id']}  {lease['worker_id']}  {lease['state']}")
    return 0


def handle_event_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)
    try:
        if args.verb == "list":
            data = {"events": list_events(paths.state_db)}
        else:
            data = {"event": inspect_event(paths.state_db, args.event_id)}
    except ObjectNotFoundError as exc:
        return emit_result(args, False, {"message": str(exc)}, 1)
    if args.json_output:
        payload = {"ok": True, "command": f"macs event {args.verb}", "data": data, "error": None}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.verb == "list":
        print(f"Events: {len(data['events'])}")
        for event in data["events"]:
            print(f"{event['event_id']}  {event['event_type']}  {event['aggregate_type']}:{event['aggregate_id']}")
    else:
        event = data["event"]
        print(f"Event: {event['event_id']}")
        print(f"Type: {event['event_type']}")
        print(f"Actor: {event['actor_type']}")
        print(f"Timestamp: {event['timestamp']}")
    return 0


def handle_overview_command(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths, _, _ = ensure_orchestration_store(repo_root)
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
    return 0


def main() -> int:
    args = parse_args()
    if args.family == "setup" and args.verb == "init":
        return handle_setup_init(args)
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
    raise SystemExit("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
