#!/usr/bin/env python3
"""Repo-local orchestration session bootstrap and controller locking."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import fcntl


RUNTIME_ADAPTERS = ("codex", "claude", "gemini", "local")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class OrchestrationPaths:
    repo_root: Path
    codex_dir: Path
    orchestration_dir: Path
    controller_lock: Path
    state_db: Path
    events_ndjson: Path
    snapshots_dir: Path
    checkpoints_dir: Path
    adapters_dir: Path


@dataclass(frozen=True)
class LockInfo:
    pid: int | None
    started_at: str | None
    repo_root: str | None
    tmux_session: str | None
    tmux_socket: str | None
    command: list[str] | None


class SessionLockHeldError(RuntimeError):
    def __init__(self, info: LockInfo):
        super().__init__("controller session lock is already held")
        self.info = info


class ControllerSessionLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.fd: int | None = None

    def acquire(self, metadata: dict[str, object]) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            info = read_lock_info(self.lock_path)
            os.close(fd)
            raise SessionLockHeldError(info) from exc

        os.ftruncate(fd, 0)
        os.write(fd, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        os.fsync(fd)
        os.set_inheritable(fd, True)
        self.fd = fd

    def release(self) -> None:
        if self.fd is None:
            return
        try:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None


def build_paths(repo_root: Path) -> OrchestrationPaths:
    codex_dir = repo_root / ".codex"
    orchestration_dir = codex_dir / "orchestration"
    return OrchestrationPaths(
        repo_root=repo_root,
        codex_dir=codex_dir,
        orchestration_dir=orchestration_dir,
        controller_lock=orchestration_dir / "controller.lock",
        state_db=orchestration_dir / "state.db",
        events_ndjson=orchestration_dir / "events.ndjson",
        snapshots_dir=orchestration_dir / "snapshots",
        checkpoints_dir=orchestration_dir / "checkpoints",
        adapters_dir=orchestration_dir / "adapters",
    )


def ensure_layout(paths: OrchestrationPaths) -> None:
    paths.codex_dir.mkdir(parents=True, exist_ok=True)
    paths.orchestration_dir.mkdir(parents=True, exist_ok=True)
    paths.controller_lock.touch(exist_ok=True)


def read_lock_info(lock_path: Path) -> LockInfo:
    if not lock_path.exists():
        return LockInfo(None, None, None, None, None, None)
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return LockInfo(None, None, None, None, None, None)
    return LockInfo(
        pid=payload.get("pid"),
        started_at=payload.get("started_at"),
        repo_root=payload.get("repo_root"),
        tmux_session=payload.get("tmux_session"),
        tmux_socket=payload.get("tmux_socket"),
        command=payload.get("command"),
    )


def build_lock_metadata(repo_root: Path) -> dict[str, object]:
    return {
        "pid": os.getpid(),
        "started_at": utc_now(),
        "repo_root": str(repo_root),
        "tmux_session": os.environ.get("TMUX_SESSION") or None,
        "tmux_socket": os.environ.get("TMUX_SOCKET") or None,
        "command": sys.argv,
    }


def render_lock_error(info: LockInfo) -> str:
    lines = ["Another controller session is already active for this repo."]
    if info.pid is not None:
        lines.append(f"Active controller pid: {info.pid}")
    if info.started_at:
        lines.append(f"Started at: {info.started_at}")
    if info.tmux_session:
        lines.append(f"tmux session: {info.tmux_session}")
    if info.tmux_socket:
        lines.append(f"tmux socket: {info.tmux_socket}")
    if info.repo_root:
        lines.append(f"Repo: {info.repo_root}")
    lines.append("Stop the active controller or use its existing terminal before starting another one.")
    return "\n".join(lines)


def setup_orchestration(repo_root: Path) -> OrchestrationPaths:
    paths = build_paths(repo_root)
    ensure_layout(paths)
    return paths
