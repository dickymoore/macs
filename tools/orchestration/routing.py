#!/usr/bin/env python3
"""Worker routing evaluation and decision persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.adapters.registry import get_adapter
from tools.orchestration.config import adapter_enabled, adapter_settings_path, load_adapter_settings
from tools.orchestration.policy import (
    evaluate_worker_governance,
    governance_policy_path,
    governance_rejection_reasons,
    load_governance_policy,
    load_routing_policy,
)
from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction
from tools.orchestration.workers import inspect_worker, list_workers


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class RoutingEvaluation:
    selected_worker_id: str | None
    ranked_candidates: list[dict[str, object]]
    rejected_workers: list[dict[str, object]]
    policy_version: str
    policy_path: str
    governance_policy_version: str
    governance_policy_path: str

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_worker_id": self.selected_worker_id,
            "ranked_candidates": self.ranked_candidates,
            "rejected_workers": self.rejected_workers,
            "policy_version": self.policy_version,
            "policy_path": self.policy_path,
            "governance_policy_version": self.governance_policy_version,
            "governance_policy_path": self.governance_policy_path,
        }


class RoutingError(RuntimeError):
    """Raised when routing cannot produce a safe eligible worker."""


def evaluate_task_routing(
    repo_root: Path,
    state_db: Path,
    task: dict[str, object],
    *,
    explicit_worker_id: str | None = None,
) -> RoutingEvaluation:
    orchestration_dir = repo_root / ".codex" / "orchestration"
    policy_path = orchestration_dir / "routing-policy.json"
    active_governance_policy_path = governance_policy_path(orchestration_dir)
    adapter_settings = load_adapter_settings(adapter_settings_path(orchestration_dir))
    policy = load_routing_policy(policy_path)
    governance_policy = load_governance_policy(active_governance_policy_path)
    workflow_defaults = policy["workflow_defaults"].get(task["workflow_class"])
    if workflow_defaults is None:
        raise RoutingError(f"Unsupported workflow class: {task['workflow_class']}")
    workers = list_workers(state_db)
    ranked_candidates: list[dict[str, object]] = []
    rejected_workers: list[dict[str, object]] = []

    for worker in workers:
        reasons = []
        if explicit_worker_id is not None and worker["worker_id"] != explicit_worker_id:
            reasons.append("not_explicit_target")
        if not adapter_enabled(adapter_settings, str(worker["adapter_id"])):
            reasons.append("adapter_disabled")
        if worker["state"] in workflow_defaults.get("disallowed_states", []):
            reasons.append(f"state:{worker['state']}")
        if worker["state"] not in {"ready", "busy"}:
            reasons.append(f"not_routable:{worker['state']}")
        if worker["freshness_seconds"] > 60:
            reasons.append("stale_evidence")
        if workflow_defaults.get("require_interruptibility") and worker["interruptibility"] != "interruptible":
            reasons.append("interruptibility_required")
        if workflow_defaults.get("forbid_networked_tools") and worker["runtime"] != "local":
            reasons.append("privacy_sensitive_local_only")
        adapter = get_adapter(str(worker["adapter_id"]))
        adapter_descriptor = adapter.descriptor()
        governance = evaluate_worker_governance(
            worker,
            adapter_descriptor,
            governance_policy,
            workflow_class=str(task["workflow_class"]),
        )
        adapter_probe_warning = None
        if governance["surface_version_pins"].get("probe_required"):
            adapter_evidence = []
            try:
                adapter_evidence = adapter.probe(worker)
            except RuntimeError as exc:
                adapter_probe_warning = str(exc)
            governance = evaluate_worker_governance(
                worker,
                adapter_descriptor,
                governance_policy,
                workflow_class=str(task["workflow_class"]),
                adapter_evidence=adapter_evidence,
                enforce_surface_version_pins=True,
            )
            if adapter_probe_warning is not None:
                governance["surface_version_pins"]["probe_error"] = adapter_probe_warning
        reasons.extend(governance_rejection_reasons(governance))
        missing_capabilities = sorted(set(task["required_capabilities"]) - set(worker["capabilities"]))
        if missing_capabilities:
            reasons.append(f"missing_capabilities:{','.join(missing_capabilities)}")
        preferred_runtimes = workflow_defaults.get("preferred_runtimes", [])
        runtime_rank = preferred_runtimes.index(worker["runtime"]) if worker["runtime"] in preferred_runtimes else 99
        candidate = {
            "worker_id": worker["worker_id"],
            "runtime": worker["runtime"],
            "state": worker["state"],
            "freshness_seconds": worker["freshness_seconds"],
            "runtime_rank": runtime_rank,
            "reasons": reasons,
            "governance": governance,
        }
        if adapter_probe_warning is not None:
            candidate["adapter_probe_warning"] = adapter_probe_warning
        if reasons:
            rejected_workers.append(candidate)
        else:
            ranked_candidates.append(candidate)

    ranked_candidates.sort(key=lambda item: (item["runtime_rank"], item["freshness_seconds"], item["worker_id"]))
    selected_worker_id = ranked_candidates[0]["worker_id"] if ranked_candidates else None
    return RoutingEvaluation(
        selected_worker_id=selected_worker_id,
        ranked_candidates=ranked_candidates,
        rejected_workers=rejected_workers,
        policy_version=policy["policy_version"],
        policy_path=str(policy_path),
        governance_policy_version=str(governance_policy["policy_version"]),
        governance_policy_path=str(active_governance_policy_path),
    )


def persist_routing_decision(
    state_db: Path,
    events_ndjson: Path,
    task_id: str,
    evaluation: RoutingEvaluation,
    *,
    lock_check_result: dict[str, object],
    secret_resolution: dict[str, object] | None = None,
) -> dict[str, object]:
    decision_id = f"route-{uuid.uuid4().hex[:12]}"
    created_at = utc_now()
    rationale = {
        "selected_worker_id": evaluation.selected_worker_id,
        "ranked_candidates": evaluation.ranked_candidates,
        "rejected_workers": evaluation.rejected_workers,
        "policy_version": evaluation.policy_version,
        "policy_path": evaluation.policy_path,
        "governance_policy_version": evaluation.governance_policy_version,
        "governance_policy_path": evaluation.governance_policy_path,
        "lock_check_result": lock_check_result,
    }
    if isinstance(secret_resolution, dict):
        rationale["secret_resolution"] = secret_resolution
    event = EventRecord(
        event_id=f"evt-routing-{uuid.uuid4().hex[:12]}",
        event_type="routing.decision_recorded",
        aggregate_type="task",
        aggregate_id=task_id,
        timestamp=created_at,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-routing-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload=rationale,
        redaction_level="none",
    )

    def mutator(conn) -> None:
        conn.execute(
            """
            INSERT INTO routing_decisions(decision_id, task_id, selected_worker_id, rationale, evidence_ref, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                task_id,
                evaluation.selected_worker_id,
                json.dumps(rationale, sort_keys=True),
                json.dumps(
                    {
                        "policy_path": evaluation.policy_path,
                        "governance_policy_path": evaluation.governance_policy_path,
                    },
                    sort_keys=True,
                ),
                created_at,
            ),
        )

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
    return {
        "decision_id": decision_id,
        "task_id": task_id,
        "selected_worker_id": evaluation.selected_worker_id,
        "rationale": rationale,
        "created_at": created_at,
    }


def routing_blocking_condition(rejected_workers: list[dict[str, object]]) -> str:
    reasons = {reason for worker in rejected_workers for reason in worker.get("reasons", [])}
    has_privacy_local_only = "privacy_sensitive_local_only" in reasons
    has_governance = any(reason.startswith("governed_surface_") or reason.startswith("undeclared_governed_surface:") for reason in reasons)
    surface_version_failures = _surface_version_failure_labels(reasons)
    has_surface_version = bool(surface_version_failures)
    has_disabled_adapter = "adapter_disabled" in reasons
    fragments = []
    if has_disabled_adapter:
        fragments.append("repo-local adapter settings disabled the available workers")
    if has_privacy_local_only:
        fragments.append("privacy-sensitive routing rejected non-local workers")
    if has_governance:
        fragments.append("governance policy rejected governed surfaces for the available workers")
    if has_surface_version:
        suffix = f" ({', '.join(surface_version_failures)})" if surface_version_failures else ""
        fragments.append(f"surface version pin enforcement rejected the available workers{suffix}")
    if fragments:
        return _join_reason_fragments(fragments)
    if has_disabled_adapter and not (has_privacy_local_only or has_governance or has_surface_version):
        return "repo-local adapter settings disabled the available workers"
    if has_privacy_local_only:
        return "privacy-sensitive routing rejected non-local workers"
    if has_governance:
        return "governance policy rejected governed surfaces for the available workers"
    return "last routing attempt found no eligible workers"


def routing_next_action(
    *,
    task_id: str,
    rejected_workers: list[dict[str, object]],
    governance_policy_path: str | None = None,
    adapter_settings_path: str | None = None,
) -> str:
    reasons = {reason for worker in rejected_workers for reason in worker.get("reasons", [])}
    has_privacy_local_only = "privacy_sensitive_local_only" in reasons
    has_governance = any(reason.startswith("governed_surface_") or reason.startswith("undeclared_governed_surface:") for reason in reasons)
    has_surface_version = bool(_surface_version_failure_labels(reasons))
    has_disabled_adapter = "adapter_disabled" in reasons
    if has_disabled_adapter and adapter_settings_path:
        return f"inspect {adapter_settings_path}, enable a safe adapter, then retry task {task_id}"
    action_steps = []
    if has_privacy_local_only:
        action_steps.append("register or select a local worker")
    if has_surface_version:
        if governance_policy_path:
            action_steps.append(f"inspect rejected workers, probe live version evidence, and review {governance_policy_path}")
        else:
            action_steps.append("inspect rejected workers and probe live version evidence")
    elif has_governance:
        if governance_policy_path:
            action_steps.append(f"inspect rejected workers and review {governance_policy_path}")
        else:
            action_steps.append("inspect rejected workers and governance policy")
    if action_steps:
        return f"{_join_reason_fragments(action_steps)} before retrying task {task_id}"
    return f"inspect the last routing decision for task {task_id} before retrying"


def inspect_routing_decision(state_db: Path, task_id: str) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT decision_id, task_id, selected_worker_id, rationale, evidence_ref, created_at
            FROM routing_decisions
            WHERE task_id = ?
            ORDER BY created_at DESC, decision_id DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "decision_id": row["decision_id"],
        "task_id": row["task_id"],
        "selected_worker_id": row["selected_worker_id"],
        "rationale": json.loads(row["rationale"]),
        "evidence_ref": json.loads(row["evidence_ref"]),
        "created_at": row["created_at"],
    }


def _surface_version_failure_labels(reasons: set[str]) -> list[str]:
    labels = []
    for prefix, label in (
        ("surface_version_pin_mismatch:", "mismatch"),
        ("surface_version_evidence_missing:", "missing evidence"),
        ("surface_version_evidence_stale:", "stale evidence"),
        ("surface_version_evidence_untrusted:", "low-trust evidence"),
    ):
        if any(reason.startswith(prefix) for reason in reasons):
            labels.append(label)
    return labels


def _join_reason_fragments(fragments: list[str]) -> str:
    if not fragments:
        return ""
    if len(fragments) == 1:
        return fragments[0]
    if len(fragments) == 2:
        return f"{fragments[0]} and {fragments[1]}"
    return ", ".join(fragments[:-1]) + f", and {fragments[-1]}"
