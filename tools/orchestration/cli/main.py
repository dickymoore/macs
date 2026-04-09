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
    render_lock_error,
    setup_orchestration,
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
            if data.get("holding_lock"):
                print("Controller session lock acquired.")
        else:
            print(data["message"], file=sys.stderr)
    return exit_code


def handle_setup_init(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo).resolve()
    paths = setup_orchestration(repo_root)
    lock = ControllerSessionLock(paths.controller_lock)
    data = {
        "repo_root": str(repo_root),
        "orchestration_dir": str(paths.orchestration_dir),
        "controller_lock": str(paths.controller_lock),
        "holding_lock": False,
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


def main() -> int:
    args = parse_args()
    if args.family == "setup" and args.verb == "init":
        return handle_setup_init(args)
    raise SystemExit("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
