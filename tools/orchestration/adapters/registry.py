#!/usr/bin/env python3
"""Runtime adapter registry."""

from __future__ import annotations

from tools.orchestration.adapters.base import BaseTmuxAdapter
from tools.orchestration.adapters.codex import CodexAdapter


def build_adapter_registry() -> dict[str, BaseTmuxAdapter]:
    return {
        "codex": CodexAdapter(),
        "claude": BaseTmuxAdapter(
            adapter_id="claude",
            runtime_type="claude",
            degraded_mode="Uses controller-observed tmux facts when Claude-specific telemetry is missing or stale.",
            unsupported_features=["token_budget", "structured_progress"],
            qualification_status="provisional",
        ),
        "gemini": BaseTmuxAdapter(
            adapter_id="gemini",
            runtime_type="gemini",
            degraded_mode="Treats missing runtime signals as degraded and preserves only required pane and capability facts.",
            unsupported_features=["token_budget", "runtime_checkpoints"],
            qualification_status="provisional",
        ),
        "local": BaseTmuxAdapter(
            adapter_id="local",
            runtime_type="local",
            degraded_mode="Keeps routing local-first and relies on tmux facts plus declared capabilities in low-signal mode.",
            unsupported_features=["token_budget", "structured_progress", "delivery_metadata"],
            qualification_status="provisional",
        ),
    }


def list_adapters() -> list[dict[str, object]]:
    return [adapter.descriptor() for adapter in build_adapter_registry().values()]


def get_adapter(adapter_id: str) -> BaseTmuxAdapter:
    registry = build_adapter_registry()
    if adapter_id not in registry:
        raise RuntimeError(f"Unknown adapter: {adapter_id}")
    return registry[adapter_id]
