#!/usr/bin/env python3
"""Codex-specific adapter behavior."""

from __future__ import annotations

import re

from tools.orchestration.adapters.base import BaseTmuxAdapter, EvidenceEnvelope, utc_now


class CodexAdapter(BaseTmuxAdapter):
    def __init__(self) -> None:
        super().__init__(
            adapter_id="codex",
            runtime_type="codex",
            degraded_mode="Falls back to tmux-observed pane presence and declared capabilities when Codex CLI flags are unavailable.",
            unsupported_features=["token_budget", "structured_progress", "checkpoint_hints"],
            qualification_status="reference",
        )

    def probe(self, worker: dict[str, object]) -> list[dict[str, object]]:
        evidence = super().probe(worker)
        observed_at = utc_now()
        source_ref = f"tmux:{worker['tmux_session']}:{worker['tmux_pane']}"
        capture = self.capture(worker, lines_or_cursor=80)["output"]
        permission_value = {
            "approval_policy": "unknown",
            "sandbox": "unknown",
            "model": "unknown",
        }
        confidence = "low"
        if "codex" in capture:
            permission_value["approval_policy"] = "yolo" if "--yolo" in capture else "guarded"
            sandbox_match = re.search(r"--sandbox(?:\s|=)+([A-Za-z0-9._-]+)", capture)
            model_match = re.search(r"--model(?:\s|=)+([A-Za-z0-9._-]+)", capture)
            if sandbox_match:
                permission_value["sandbox"] = sandbox_match.group(1)
            if model_match:
                permission_value["model"] = model_match.group(1)
            confidence = "medium"

        evidence.append(
            EvidenceEnvelope(
                adapter_id=self.adapter_id,
                worker_id=worker["worker_id"],
                observed_at=observed_at,
                kind="claim",
                name="permission_surface",
                value=permission_value,
                freshness_seconds=worker["freshness_seconds"],
                confidence=confidence,
                source_ref=source_ref,
            ).as_dict()
        )
        return evidence
