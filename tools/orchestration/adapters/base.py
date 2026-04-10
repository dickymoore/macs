#!/usr/bin/env python3
"""Shared runtime adapter contract and tmux-backed base implementation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class EvidenceEnvelope:
    adapter_id: str
    worker_id: str
    observed_at: str
    kind: str
    name: str
    value: dict[str, object]
    freshness_seconds: int
    confidence: str
    source_ref: str

    def as_dict(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "worker_id": self.worker_id,
            "observed_at": self.observed_at,
            "kind": self.kind,
            "name": self.name,
            "value": self.value,
            "freshness_seconds": self.freshness_seconds,
            "confidence": self.confidence,
            "source_ref": self.source_ref,
        }


class BaseTmuxAdapter:
    def __init__(
        self,
        *,
        adapter_id: str,
        runtime_type: str,
        degraded_mode: str,
        unsupported_features: list[str],
        qualification_status: str,
    ):
        self.adapter_id = adapter_id
        self.runtime_type = runtime_type
        self.degraded_mode = degraded_mode
        self.unsupported_features = unsupported_features
        self.qualification_status = qualification_status

    def descriptor(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "runtime_type": self.runtime_type,
            "supported_operations": [
                "discover_workers",
                "probe",
                "dispatch",
                "capture",
                "interrupt",
                "acknowledge_delivery",
            ],
            "unsupported_features": self.unsupported_features,
            "degraded_mode_behavior": self.degraded_mode,
            "qualification_status": self.qualification_status,
        }

    def discover_workers(self, repo_root, **kwargs) -> list[dict[str, object]]:
        from tools.orchestration.workers import discover_tmux_workers

        workers = discover_tmux_workers(repo_root, **kwargs)
        return [worker.as_dict() for worker in workers if worker.adapter_id == self.adapter_id]

    def probe(self, worker: dict[str, object]) -> list[dict[str, object]]:
        observed_at = utc_now()
        source_ref = f"tmux:{worker['tmux_session']}:{worker['tmux_pane']}"
        evidence = [
            EvidenceEnvelope(
                adapter_id=self.adapter_id,
                worker_id=worker["worker_id"],
                observed_at=observed_at,
                kind="fact",
                name="pane_presence",
                value={
                    "tmux_session": worker["tmux_session"],
                    "tmux_pane": worker["tmux_pane"],
                    "state": worker["state"],
                },
                freshness_seconds=worker["freshness_seconds"],
                confidence="high",
                source_ref=source_ref,
            ),
            EvidenceEnvelope(
                adapter_id=self.adapter_id,
                worker_id=worker["worker_id"],
                observed_at=observed_at,
                kind="fact",
                name="capability_decl",
                value={"capabilities": worker["capabilities"]},
                freshness_seconds=worker["freshness_seconds"],
                confidence="high",
                source_ref=source_ref,
            ),
            EvidenceEnvelope(
                adapter_id=self.adapter_id,
                worker_id=worker["worker_id"],
                observed_at=observed_at,
                kind="signal",
                name="health_state",
                value={
                    "required_signal_status": worker["required_signal_status"],
                    "interruptibility": worker["interruptibility"],
                    "unsupported_features": self.unsupported_features,
                },
                freshness_seconds=worker["freshness_seconds"],
                confidence="medium",
                source_ref=source_ref,
            ),
        ]
        return [item.as_dict() for item in evidence]

    def dispatch(self, worker: dict[str, object], assignment_payload: str) -> dict[str, object]:
        self._send_keys(worker, [assignment_payload, "Enter"])
        return {"ok": True, "adapter_id": self.adapter_id, "worker_id": worker["worker_id"]}

    def capture(self, worker: dict[str, object], lines_or_cursor: int = 40) -> dict[str, object]:
        result = subprocess.run(
            [
                "tmux",
                "-S",
                worker["tmux_socket"],
                "capture-pane",
                "-p",
                "-t",
                worker["tmux_pane"],
                "-S",
                f"-{lines_or_cursor}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "tmux capture-pane failed")
        return {"ok": True, "adapter_id": self.adapter_id, "worker_id": worker["worker_id"], "output": result.stdout}

    def interrupt(self, worker: dict[str, object]) -> dict[str, object]:
        self._send_keys(worker, ["C-c"])
        return {"ok": True, "adapter_id": self.adapter_id, "worker_id": worker["worker_id"]}

    def acknowledge_delivery(self, worker: dict[str, object], correlation_id: str) -> dict[str, object]:
        return {
            "ok": True,
            "adapter_id": self.adapter_id,
            "worker_id": worker["worker_id"],
            "correlation_id": correlation_id,
            "acknowledged_at": utc_now(),
        }

    def validate_contract(self) -> dict[str, object]:
        required_operations = [
            "discover_workers",
            "probe",
            "dispatch",
            "capture",
            "interrupt",
            "acknowledge_delivery",
        ]
        checks = {
            "required_operations_present": all(callable(getattr(self, name, None)) for name in required_operations),
            "unsupported_features_declared": isinstance(self.unsupported_features, list),
            "degraded_mode_declared": bool(self.degraded_mode),
        }
        checks["ok"] = all(checks.values())
        checks["required_operations"] = required_operations
        checks["unsupported_features"] = self.unsupported_features
        return checks

    def _send_keys(self, worker: dict[str, object], keys: list[str]) -> None:
        result = subprocess.run(
            ["tmux", "-S", worker["tmux_socket"], "send-keys", "-t", worker["tmux_pane"], *keys],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "tmux send-keys failed")
