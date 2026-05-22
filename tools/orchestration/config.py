#!/usr/bin/env python3
"""Repo-local configuration domain defaults and loaders."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONTROLLER_DEFAULTS = {
    "defaults_version": "phase1-controller-defaults-v1",
    "task": {
        "default_workflow_class": "implementation",
        "default_priority": "normal",
    },
}

DEFAULT_ADAPTER_SETTINGS = {
    "settings_version": "phase1-adapter-settings-v1",
    "adapters": {
        "codex": {
            "enabled": True,
            "config_ref": ".codex/tmux-worker.env",
            "notes": "tmux-backed worker defaults remain repo-local and bridge-compatible",
        },
        "claude": {
            "enabled": True,
            "config_ref": ".codex/tmux-worker.env",
            "notes": "shares repo-local tmux worker defaults when the runtime is launched through MACS",
        },
        "gemini": {
            "enabled": True,
            "config_ref": ".codex/tmux-worker.env",
            "notes": "shares repo-local tmux worker defaults when the runtime is launched through MACS",
        },
        "local": {
            "enabled": True,
            "config_ref": ".codex/tmux-worker.env",
            "notes": "uses the same local tmux worker defaults unless overridden by the operator",
        },
    },
}

DEFAULT_STATE_LAYOUT = {
    "layout_version": "phase1-state-layout-v1",
    "paths": {
        "controller_lock": "controller.lock",
        "state_db": "state.db",
        "events_ndjson": "events.ndjson",
        "snapshots_dir": "snapshots",
        "checkpoints_dir": "checkpoints",
        "adapters_dir": "adapters",
    },
    "compatibility_paths": {
        "tmux_session_file": ".codex/tmux-session.txt",
        "tmux_socket_file": ".codex/tmux-socket.txt",
        "target_pane_file": ".codex/target-pane.txt",
        "legacy_target_pane_file": "tools/tmux_bridge/target_pane.txt",
        "worker_tmux_env_file": ".codex/tmux-worker.env",
    },
}


@dataclass(frozen=True)
class ConfigBootstrapResult:
    controller_defaults_path_created: bool
    adapter_settings_path_created: bool
    state_layout_path_created: bool
    controller_defaults_path: Path
    adapter_settings_path: Path
    state_layout_path: Path


def controller_defaults_path(orchestration_dir: Path) -> Path:
    return orchestration_dir / "controller-defaults.json"


def adapter_settings_path(orchestration_dir: Path) -> Path:
    return orchestration_dir / "adapter-settings.json"


def state_layout_path(orchestration_dir: Path) -> Path:
    return orchestration_dir / "state-layout.json"


def bootstrap_config_domains(orchestration_dir: Path) -> ConfigBootstrapResult:
    controller_path = controller_defaults_path(orchestration_dir)
    adapter_path = adapter_settings_path(orchestration_dir)
    state_path = state_layout_path(orchestration_dir)
    return ConfigBootstrapResult(
        controller_defaults_path_created=_bootstrap_json_file(
            controller_path,
            DEFAULT_CONTROLLER_DEFAULTS,
        ),
        adapter_settings_path_created=_bootstrap_json_file(
            adapter_path,
            DEFAULT_ADAPTER_SETTINGS,
        ),
        state_layout_path_created=_bootstrap_json_file(
            state_path,
            DEFAULT_STATE_LAYOUT,
        ),
        controller_defaults_path=controller_path,
        adapter_settings_path=adapter_path,
        state_layout_path=state_path,
    )


def load_controller_defaults(path: Path) -> dict[str, object]:
    return _load_json(path)


def load_adapter_settings(path: Path) -> dict[str, object]:
    return _load_json(path)


def load_state_layout(path: Path) -> dict[str, object]:
    return _load_json(path)


def state_layout_or_default(path: Path) -> dict[str, object]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_STATE_LAYOUT))
    return load_state_layout(path)


def controller_defaults_or_default(path: Path) -> dict[str, object]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_CONTROLLER_DEFAULTS))
    return load_controller_defaults(path)


def adapter_settings_or_default(path: Path) -> dict[str, object]:
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_ADAPTER_SETTINGS))
    return load_adapter_settings(path)


def resolved_state_paths(repo_root: Path, orchestration_dir: Path, state_layout: dict[str, object]) -> dict[str, Path]:
    raw_paths = state_layout.get("paths", {})
    return {
        "controller_lock": _resolve_layout_path(orchestration_dir, raw_paths.get("controller_lock"), "controller.lock"),
        "state_db": _resolve_layout_path(orchestration_dir, raw_paths.get("state_db"), "state.db"),
        "events_ndjson": _resolve_layout_path(orchestration_dir, raw_paths.get("events_ndjson"), "events.ndjson"),
        "snapshots_dir": _resolve_layout_path(orchestration_dir, raw_paths.get("snapshots_dir"), "snapshots"),
        "checkpoints_dir": _resolve_layout_path(orchestration_dir, raw_paths.get("checkpoints_dir"), "checkpoints"),
        "adapters_dir": _resolve_layout_path(orchestration_dir, raw_paths.get("adapters_dir"), "adapters"),
    }


def resolved_compatibility_paths(repo_root: Path, state_layout: dict[str, object]) -> dict[str, Path]:
    raw_paths = state_layout.get("compatibility_paths", {})
    return {
        "tmux_session_file": _resolve_repo_relative_path(repo_root, raw_paths.get("tmux_session_file"), ".codex/tmux-session.txt"),
        "tmux_socket_file": _resolve_repo_relative_path(repo_root, raw_paths.get("tmux_socket_file"), ".codex/tmux-socket.txt"),
        "target_pane_file": _resolve_repo_relative_path(repo_root, raw_paths.get("target_pane_file"), ".codex/target-pane.txt"),
        "legacy_target_pane_file": _resolve_repo_relative_path(
            repo_root,
            raw_paths.get("legacy_target_pane_file"),
            "tools/tmux_bridge/target_pane.txt",
        ),
        "worker_tmux_env_file": _resolve_repo_relative_path(
            repo_root,
            raw_paths.get("worker_tmux_env_file"),
            ".codex/tmux-worker.env",
        ),
    }


def adapter_configuration(adapter_settings: dict[str, object], adapter_id: str) -> dict[str, object]:
    adapters = adapter_settings.get("adapters", {})
    if isinstance(adapters, dict) and adapter_id in adapters and isinstance(adapters[adapter_id], dict):
        config = dict(adapters[adapter_id])
    else:
        config = {"enabled": True}
    config.setdefault("enabled", True)
    config.setdefault("config_ref", ".codex/tmux-worker.env")
    config.setdefault("notes", "")
    return config


def resolve_adapter_config_ref(repo_root: Path, adapter_settings: dict[str, object], adapter_id: str) -> Path:
    config_ref = adapter_configuration(adapter_settings, adapter_id).get("config_ref")
    text = str(config_ref or ".codex/tmux-worker.env").strip() or ".codex/tmux-worker.env"
    candidate = Path(text).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (repo_root / candidate).resolve(strict=False)


def adapter_secret_source_paths(repo_root: Path, adapter_settings: dict[str, object], adapter_id: str) -> list[Path]:
    """Return the bounded local secret-source paths for one adapter in precedence order."""

    candidates = [
        resolve_adapter_config_ref(repo_root, adapter_settings, adapter_id),
        (repo_root / ".codex" / "tmux-worker.env").expanduser().resolve(strict=False),
        Path("~/.config/macs/tmux-worker.env").expanduser().resolve(strict=False),
    ]
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in candidates:
        marker = str(path)
        if marker in seen:
            continue
        seen.add(marker)
        ordered.append(path)
    return ordered


def adapter_enabled(adapter_settings: dict[str, object], adapter_id: str) -> bool:
    return bool(adapter_configuration(adapter_settings, adapter_id).get("enabled", True))


def adapter_settings_summary(adapter_settings: dict[str, object]) -> dict[str, object]:
    adapters = adapter_settings.get("adapters", {})
    enabled = []
    disabled = []
    if isinstance(adapters, dict):
        for adapter_id in sorted(adapters):
            if adapter_enabled(adapter_settings, adapter_id):
                enabled.append(adapter_id)
            else:
                disabled.append(adapter_id)
    return {
        "enabled_adapters": enabled,
        "disabled_adapters": disabled,
    }


def _bootstrap_json_file(path: Path, default_payload: dict[str, object]) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_layout_path(orchestration_dir: Path, raw_value: object, default_value: str) -> Path:
    text = str(raw_value or default_value)
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate
    return orchestration_dir / candidate


def _resolve_repo_relative_path(repo_root: Path, raw_value: object, default_value: str) -> Path:
    text = str(raw_value or default_value)
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate
