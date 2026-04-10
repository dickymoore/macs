#!/usr/bin/env python3
"""Shared runtime adapter contract and tmux-backed base implementation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone


REQUIRED_FACTS = [
    "stable_worker_identity",
    "runtime_type",
    "tmux_location",
    "capability_declaration",
    "freshness_timestamp",
    "interruptibility_support",
    "degraded_mode_declaration",
]

REQUIRED_OPERATIONS = [
    "discover_workers",
    "probe",
    "dispatch",
    "capture",
    "interrupt",
    "acknowledge_delivery",
]

PHASE1_REFERENCE_WORKFLOW_CLASSES = [
    "documentation_context",
    "planning_docs",
    "solutioning",
    "implementation",
    "review",
    "privacy_sensitive_offline",
]

QUALIFICATION_EXPECTATIONS = [
    "shared_contract_suite",
    "unsupported_feature_declarations",
    "degraded_mode_behavior",
    "controller_mediated_intervention",
    "routing_evidence_support",
    "supported_feature_regressions",
]

SHARED_VALIDATION_COMMANDS = [
    "python3 -m unittest tools.orchestration.tests.test_adapter_contracts",
    "python3 -m unittest tools.orchestration.tests.test_controller_invariants",
    "python3 -m unittest tools.orchestration.tests.test_setup_init",
    "python3 -m unittest discover -s tools/orchestration/tests",
    "macs adapter inspect --adapter <adapter-id> --json",
    "macs adapter validate --adapter <adapter-id> --json",
]

RELEASE_GATE_CRITERIA = [
    "RG1:evidence_based_first_class_qualification",
    "RG8:contributor_guidance_alignment",
]


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
        optional_enrichments: list[str] | None = None,
        governed_surfaces: list[str] | None = None,
    ):
        self.adapter_id = adapter_id
        self.runtime_type = runtime_type
        self.degraded_mode = degraded_mode
        self.unsupported_features = unsupported_features
        self.qualification_status = qualification_status
        self.optional_enrichments = optional_enrichments or []
        self.governed_surfaces = governed_surfaces or []

    def descriptor(self) -> dict[str, object]:
        contract = {
            "required_facts": list(REQUIRED_FACTS),
            "required_operations": list(REQUIRED_OPERATIONS),
            "capability_model": {
                "declaration_field": "capabilities",
                "evidence_name": "capability_decl",
                "reference_workflow_classes": list(PHASE1_REFERENCE_WORKFLOW_CLASSES),
                "notes": (
                    "Workers declare string capabilities; Phase 1 routing defaults and regression coverage "
                    "use the workflow-class labels as the reference vocabulary."
                ),
            },
            "optional_enrichments": {
                "implemented": list(self.optional_enrichments),
                "unsupported": list(self.unsupported_features),
            },
            "degraded_mode_expectations": {
                "behavior": self.degraded_mode,
                "controller_authority_preserved": True,
                "unsupported_features_must_be_declared": True,
            },
            "qualification_expectations": list(QUALIFICATION_EXPECTATIONS),
            "validation_commands": list(SHARED_VALIDATION_COMMANDS),
            "release_gate_criteria": list(RELEASE_GATE_CRITERIA),
        }
        return {
            "adapter_id": self.adapter_id,
            "runtime_type": self.runtime_type,
            "supported_operations": list(REQUIRED_OPERATIONS),
            "unsupported_features": self.unsupported_features,
            "governed_surfaces": self.governed_surfaces,
            "degraded_mode_behavior": self.degraded_mode,
            "qualification_status": self.qualification_status,
            "contract": contract,
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
        contract = self.descriptor()["contract"]
        checks = {
            "required_operations_present": all(callable(getattr(self, name, None)) for name in REQUIRED_OPERATIONS),
            "required_facts_declared": contract["required_facts"] == REQUIRED_FACTS,
            "capability_model_declared": (
                contract["capability_model"]["declaration_field"] == "capabilities"
                and contract["capability_model"]["evidence_name"] == "capability_decl"
                and bool(contract["capability_model"]["reference_workflow_classes"])
            ),
            "unsupported_features_declared": isinstance(self.unsupported_features, list),
            "degraded_mode_declared": bool(self.degraded_mode),
            "qualification_expectations_declared": bool(contract["qualification_expectations"]),
        }
        checks["ok"] = all(checks.values())
        checks["required_operations"] = list(REQUIRED_OPERATIONS)
        checks["required_facts"] = list(REQUIRED_FACTS)
        checks["capability_model"] = contract["capability_model"]
        checks["qualification_expectations"] = contract["qualification_expectations"]
        checks["validation_commands"] = contract["validation_commands"]
        checks["release_gate_criteria"] = contract["release_gate_criteria"]
        checks["unsupported_features"] = self.unsupported_features
        return checks

    def qualification_gate(
        self,
        validation: dict[str, object] | None = None,
        *,
        release_candidate: bool | None = None,
    ) -> dict[str, object]:
        validation = validation or self.validate_contract()
        declared_first_class_candidate = self.qualification_status == "reference"
        release_gate_candidate = declared_first_class_candidate if release_candidate is None else release_candidate
        shared_contract_passed = bool(validation.get("ok"))
        blocked_reasons: list[str] = []
        if release_gate_candidate and not shared_contract_passed:
            blocked_reasons.append("shared_contract_failed")
        return {
            "declared_status": self.qualification_status,
            "declared_first_class_candidate": declared_first_class_candidate,
            "release_gate_candidate": release_gate_candidate,
            "shared_contract_passed": shared_contract_passed,
            "first_class_eligible": release_gate_candidate and shared_contract_passed,
            "blocked_reasons": blocked_reasons,
        }

    def _send_keys(self, worker: dict[str, object], keys: list[str]) -> None:
        result = subprocess.run(
            ["tmux", "-S", worker["tmux_socket"], "send-keys", "-t", worker["tmux_pane"], *keys],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "tmux send-keys failed")
