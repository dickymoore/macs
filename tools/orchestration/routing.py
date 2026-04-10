#!/usr/bin/env python3
"""Worker routing evaluation and decision persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.policy import load_routing_policy
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

    def as_dict(self) -> dict[str, object]:
        return {
            "selected_worker_id": self.selected_worker_id,
            "ranked_candidates": self.ranked_candidates,
            "rejected_workers": self.rejected_workers,
            "policy_version": self.policy_version,
            "policy_path": self.policy_path,
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
    policy_path = repo_root / ".codex" / "orchestration" / "routing-policy.json"
    policy = load_routing_policy(policy_path)
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
        }
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
    )


def persist_routing_decision(
    state_db: Path,
    events_ndjson: Path,
    task_id: str,
    evaluation: RoutingEvaluation,
    *,
    lock_check_result: dict[str, object],
) -> dict[str, object]:
    decision_id = f"route-{uuid.uuid4().hex[:12]}"
    created_at = utc_now()
    rationale = {
        "selected_worker_id": evaluation.selected_worker_id,
        "ranked_candidates": evaluation.ranked_candidates,
        "rejected_workers": evaluation.rejected_workers,
        "policy_version": evaluation.policy_version,
        "policy_path": evaluation.policy_path,
        "lock_check_result": lock_check_result,
    }
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
                json.dumps({"policy_path": evaluation.policy_path}, sort_keys=True),
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
