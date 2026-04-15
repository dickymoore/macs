#!/usr/bin/env python3
"""Lease and event inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path

from tools.orchestration.policy import active_governance_snapshot, governance_policy_path, load_governance_policy
from tools.orchestration.store import connect_state_db


class ObjectNotFoundError(RuntimeError):
    """Raised when an inspected object does not exist."""


def _load_payload(raw_payload: str | None) -> dict[str, object]:
    if not raw_payload:
        return {}
    return json.loads(raw_payload)


def _load_json_object(raw_payload: str | None) -> dict[str, object]:
    if not raw_payload:
        return {}
    return json.loads(raw_payload)


def _affected_refs_from_payload(payload: dict[str, object]) -> dict[str, object] | None:
    affected_refs = payload.get("affected_refs")
    if isinstance(affected_refs, dict):
        return affected_refs

    derived = {}
    for key in (
        "task_id",
        "lease_id",
        "worker_id",
        "surface_id",
        "secret_ref",
        "recovery_run_id",
        "replacement_lease_id",
        "previous_lease_id",
        "predecessor_lease_id",
        "selected_worker_id",
    ):
        value = payload.get(key)
        if value is not None:
            derived[key] = value
    return derived or None


def _event_summary(row, *, include_payload: bool) -> dict[str, object]:
    payload = _load_payload(row["payload"])
    item = {
        "event_id": row["event_id"],
        "event_type": row["event_type"],
        "aggregate_type": row["aggregate_type"],
        "aggregate_id": row["aggregate_id"],
        "timestamp": row["timestamp"],
        "actor_type": row["actor_type"],
        "actor_id": row["actor_id"],
        "correlation_id": row["correlation_id"],
        "causation_id": row["causation_id"],
        "intervention_rationale": payload.get("intervention_rationale"),
        "decision_event_id": payload.get("decision_event_id"),
        "decision_action": payload.get("decision_action"),
        "checkpoint_id": payload.get("checkpoint_id"),
        "target_action": payload.get("target_action"),
        "affected_refs": _affected_refs_from_payload(payload),
        "redaction_level": row["redaction_level"],
    }
    if include_payload:
        item["payload"] = payload
    else:
        item["payload_summary"] = payload
    return item


def list_aggregate_events(state_db: Path, aggregate_id: str, *, limit: int = 5) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                   actor_id, correlation_id, causation_id, payload, redaction_level
            FROM events
            WHERE aggregate_id = ?
            ORDER BY timestamp DESC, event_id DESC
            LIMIT ?
            """,
            (aggregate_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_event_summary(row, include_payload=False) for row in rows]


def _checkpoint_summary(row) -> dict[str, object]:
    return {
        "checkpoint_id": row["checkpoint_id"],
        "task_id": row["task_id"],
        "target_action": row["target_action"],
        "actor_type": row["actor_type"],
        "actor_id": row["actor_id"],
        "captured_at": row["captured_at"],
        "event_id": row["event_id"],
        "decision_event_id": row["decision_event_id"],
        "affected_refs": _load_json_object(row["affected_refs"]),
        "evidence_refs": _load_json_object(row["evidence_refs"]),
        "baseline_fingerprint": _load_json_object(row["baseline_fingerprint"]),
    }


CHECKPOINT_ORDER_BY = "captured_at DESC, rowid DESC"


def list_task_checkpoints(state_db: Path, task_id: str, *, limit: int = 5) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            f"""
            SELECT checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                   event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
            FROM review_checkpoints
            WHERE task_id = ?
            ORDER BY {CHECKPOINT_ORDER_BY}
            LIMIT ?
            """,
            (task_id, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_checkpoint_summary(row) for row in rows]


def latest_task_checkpoint(
    state_db: Path,
    task_id: str,
    *,
    target_action: str | None = None,
) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        if target_action is None:
            row = conn.execute(
                f"""
                SELECT checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                       event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
                FROM review_checkpoints
                WHERE task_id = ?
                ORDER BY {CHECKPOINT_ORDER_BY}
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        else:
            row = conn.execute(
                f"""
                SELECT checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                       event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
                FROM review_checkpoints
                WHERE task_id = ? AND target_action = ?
                ORDER BY {CHECKPOINT_ORDER_BY}
                LIMIT 1
                """,
                (task_id, target_action),
            ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _checkpoint_summary(row)


def inspect_checkpoint(state_db: Path, checkpoint_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                   event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
            FROM review_checkpoints
            WHERE checkpoint_id = ?
            """,
            (checkpoint_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ObjectNotFoundError(f"Checkpoint not found: {checkpoint_id}")
    return _checkpoint_summary(row)


def inspect_checkpoint_for_event(state_db: Path, event_id: str) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                   event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
            FROM review_checkpoints
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _checkpoint_summary(row)


def checkpoint_for_ref(state_db: Path, event_ref: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(event_ref, dict):
        return None
    checkpoint_id = str(event_ref.get("checkpoint_id") or "")
    if checkpoint_id:
        try:
            return inspect_checkpoint(state_db, checkpoint_id)
        except ObjectNotFoundError:
            pass
    event_id = str(event_ref.get("event_id") or "")
    if not event_id:
        return None
    return inspect_checkpoint_for_event(state_db, event_id)


def inspect_decision_event(state_db: Path, decision_event_id: str | None) -> dict[str, object] | None:
    if not decision_event_id:
        return None
    try:
        return inspect_event(state_db, decision_event_id)
    except ObjectNotFoundError:
        return None


def decision_event_for_ref(state_db: Path, event_ref: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(event_ref, dict):
        return None
    return inspect_decision_event(state_db, str(event_ref.get("decision_event_id") or ""))


def latest_intervention_decision(state_db: Path, task_id: str) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                   actor_id, correlation_id, causation_id, payload, redaction_level
            FROM events
            WHERE aggregate_id = ? AND event_type = 'intervention.decision_recorded'
            ORDER BY timestamp DESC, event_id DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _event_summary(row, include_payload=True)


def inspect_lease(state_db: Path, lease_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT lease_id, task_id, worker_id, state, issued_at, accepted_at, ended_at,
                   replacement_lease_id, intervention_reason, evidence_version
            FROM leases
            WHERE lease_id = ?
            """,
            (lease_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ObjectNotFoundError(f"Lease not found: {lease_id}")
    return dict(row)


def list_lease_history(state_db: Path, *, task_id: str | None = None, worker_id: str | None = None) -> list[dict[str, object]]:
    if not task_id and not worker_id:
        raise RuntimeError("lease history requires --task or --worker")
    conn = connect_state_db(state_db)
    try:
        if task_id:
            rows = conn.execute(
                """
                SELECT lease_id, task_id, worker_id, state, issued_at, accepted_at, ended_at, replacement_lease_id
                FROM leases
                WHERE task_id = ?
                ORDER BY issued_at, lease_id
                """,
                (task_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT lease_id, task_id, worker_id, state, issued_at, accepted_at, ended_at, replacement_lease_id
                FROM leases
                WHERE worker_id = ?
                ORDER BY issued_at, lease_id
                """,
                (worker_id,),
            ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        item = dict(row)
        latest_event_ref = None
        if item.get("lease_id"):
            recent_events = list_aggregate_events(state_db, str(item["lease_id"]), limit=1)
            latest_event_ref = recent_events[0] if recent_events else None
        item["latest_event_ref"] = latest_event_ref
        item["decision_event"] = decision_event_for_ref(state_db, latest_event_ref)
        items.append(item)
    return items


def list_events(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                   actor_id, correlation_id, causation_id, payload, redaction_level
            FROM events
            ORDER BY timestamp, event_id
            """
        ).fetchall()
    finally:
        conn.close()
    return [_event_summary(row, include_payload=False) for row in rows]


def inspect_event(state_db: Path, event_id: str) -> dict[str, object]:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                   actor_id, correlation_id, causation_id, payload, redaction_level
            FROM events
            WHERE event_id = ?
            """,
            (event_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ObjectNotFoundError(f"Event not found: {event_id}")
    return _event_summary(row, include_payload=True)


def _inspect_latest_routing_decision(state_db: Path, task_id: str) -> dict[str, object] | None:
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
        "rationale": _load_json_object(row["rationale"]),
        "evidence_ref": _load_json_object(row["evidence_ref"]),
        "created_at": row["created_at"],
    }


def _inspect_task_workflow_class(state_db: Path, task_id: str) -> str | None:
    conn = connect_state_db(state_db)
    try:
        row = conn.execute(
            """
            SELECT workflow_class
            FROM tasks
            WHERE task_id = ?
            """,
            (task_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return row["workflow_class"]


def _list_task_events_with_payload(
    state_db: Path,
    task_id: str,
    *,
    limit: int | None = 20,
) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        if limit is None:
            rows = conn.execute(
                """
                SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                       actor_id, correlation_id, causation_id, payload, redaction_level
                FROM events
                WHERE aggregate_id = ?
                ORDER BY timestamp DESC, event_id DESC
                """,
                (task_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type,
                       actor_id, correlation_id, causation_id, payload, redaction_level
                FROM events
                WHERE aggregate_id = ?
                ORDER BY timestamp DESC, event_id DESC
                LIMIT ?
                """,
                (task_id, limit),
            ).fetchall()
    finally:
        conn.close()
    return [_event_summary(row, include_payload=True) for row in rows]


def _match_task_event(
    events: list[dict[str, object]],
    *,
    event_type: str | None = None,
    payload_key: str | None = None,
    expected_value: str | None = None,
) -> dict[str, object] | None:
    for event in events:
        if event_type is not None and event.get("event_type") != event_type:
            continue
        payload = event.get("payload")
        if payload_key is None:
            return event
        if not isinstance(payload, dict):
            continue
        if str(payload.get(payload_key) or "") == str(expected_value or ""):
            return event
    return None


def _expected_surface_identities(applicable_pins: object) -> dict[str, list[str]]:
    pins = applicable_pins if isinstance(applicable_pins, list) else []
    runtime_identities = sorted(
        {
            str(pin.get("expected_runtime_identity"))
            for pin in pins
            if isinstance(pin, dict) and pin.get("expected_runtime_identity")
        }
    )
    model_identities = sorted(
        {
            str(pin.get("expected_model_identity"))
            for pin in pins
            if isinstance(pin, dict) and pin.get("expected_model_identity")
        }
    )
    return {
        "runtime_identities": runtime_identities,
        "model_identities": model_identities,
    }


def _surface_version_results_from_summary(
    summary: dict[str, object] | None,
    *,
    worker_id: str | None,
    routing_decision_id: str | None,
    related_event_id: str | None,
) -> tuple[list[dict[str, object]], str | None]:
    if not isinstance(summary, dict):
        return [], None
    version_summary = summary.get("surface_version_pins")
    if not isinstance(version_summary, dict):
        return [], None

    blocked_by_surface = {
        str(item.get("surface_id") or ""): item
        for item in version_summary.get("blocked_surfaces", [])
        if isinstance(item, dict) and item.get("surface_id")
    }
    results: list[dict[str, object]] = []
    for surface in version_summary.get("evaluated_surfaces", []):
        if not isinstance(surface, dict):
            continue
        surface_id = str(surface.get("surface_id") or "")
        if not surface_id:
            continue
        blocked_surface = blocked_by_surface.get(surface_id)
        source = blocked_surface or surface
        results.append(
            {
                "worker_id": worker_id,
                "surface_id": surface_id,
                "outcome": "blocked" if blocked_surface is not None else "matched",
                "reason": source.get("reason"),
                "selector_context": source.get("selector_context"),
                "expected": _expected_surface_identities(source.get("applicable_pins")),
                "observed": source.get("observed"),
                "failure_reasons": list(source.get("failure_reasons", [])),
                "routing_decision_id": routing_decision_id,
                "related_event_id": related_event_id,
            }
        )
    if results:
        status = "blocked" if any(item["outcome"] == "blocked" for item in results) else "matched"
        return results, status
    if version_summary.get("probe_required"):
        return (
            [
                {
                    "worker_id": worker_id,
                    "surface_id": None,
                    "outcome": "probe_required",
                    "reason": None,
                    "selector_context": None,
                    "expected": {"runtime_identities": [], "model_identities": []},
                    "observed": version_summary.get("observed"),
                    "failure_reasons": [],
                    "routing_decision_id": routing_decision_id,
                    "related_event_id": related_event_id,
                }
            ],
            "probe_required",
        )
    return [], None


def _surface_version_evidence(
    governance: dict[str, object] | None,
    routing_decision: dict[str, object] | None,
    *,
    related_event_id: str | None,
) -> dict[str, object] | None:
    routing_decision_id = str((routing_decision or {}).get("decision_id") or "") or None
    selected_worker_id = str((routing_decision or {}).get("selected_worker_id") or "") or None
    if isinstance(governance, dict) and selected_worker_id:
        results, status = _surface_version_results_from_summary(
            governance,
            worker_id=selected_worker_id,
            routing_decision_id=routing_decision_id,
            related_event_id=related_event_id,
        )
        if results:
            return {
                "status": status,
                "surface_results": results,
            }

    rationale = (routing_decision or {}).get("rationale")
    if not isinstance(rationale, dict):
        return None
    candidate_lists: list[tuple[str | None, list[object]]] = []
    ranked_candidates = rationale.get("ranked_candidates")
    rejected_workers = rationale.get("rejected_workers")
    if selected_worker_id and isinstance(ranked_candidates, list):
        selected_candidates = [
            candidate
            for candidate in ranked_candidates
            if isinstance(candidate, dict) and str(candidate.get("worker_id") or "") == selected_worker_id
        ]
        if selected_candidates:
            candidate_lists.append((selected_worker_id, selected_candidates))
    if not candidate_lists and isinstance(rejected_workers, list):
        candidate_lists.append((None, rejected_workers))

    surface_results: list[dict[str, object]] = []
    statuses: list[str] = []
    for selected_id, candidates in candidate_lists:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            results, status = _surface_version_results_from_summary(
                candidate.get("governance"),
                worker_id=str(candidate.get("worker_id") or selected_id or ""),
                routing_decision_id=routing_decision_id,
                related_event_id=related_event_id,
            )
            surface_results.extend(results)
            if status:
                statuses.append(status)
    if not surface_results:
        return None
    status = "blocked" if "blocked" in statuses else statuses[0]
    return {
        "status": status,
        "surface_results": surface_results,
    }


def _secret_scope_evidence(
    secret_resolution: dict[str, object] | None,
    *,
    routing_decision_id: str | None,
    related_event_id: str | None,
) -> dict[str, object] | None:
    if not isinstance(secret_resolution, dict):
        return None
    status = str(secret_resolution.get("status") or "")
    if not status or status == "not_required":
        return None
    surface_results: list[dict[str, object]] = []
    for surface in secret_resolution.get("surface_summaries", []):
        if not isinstance(surface, dict):
            continue
        secret_refs = (
            list(surface.get("resolved_secret_refs", []))
            or list(surface.get("required_secret_refs", []))
            or list(surface.get("unresolved_secret_refs", []))
        )
        surface_results.append(
            {
                "surface_id": surface.get("surface_id"),
                "outcome": "blocked" if surface.get("reason") else "resolved",
                "reason": surface.get("reason"),
                "secret_ref": secret_refs[0] if secret_refs else None,
                "secret_refs": secret_refs,
                "selector_context": surface.get("selector_context"),
                "delivery_mode": surface.get("delivery_mode"),
                "routing_decision_id": routing_decision_id,
                "related_event_id": related_event_id,
            }
        )
    return {
        "status": status,
        "reason": secret_resolution.get("reason"),
        "surface_results": surface_results,
    }


def _checkpoint_baseline_summary(baseline_fingerprint: object) -> str | None:
    if not isinstance(baseline_fingerprint, dict):
        return None
    head = baseline_fingerprint.get("head") or {}
    dirty_state = baseline_fingerprint.get("dirty_state") or {}
    affected_paths = baseline_fingerprint.get("affected_paths") or []
    parts = [f"head_state={head.get('state') or 'unknown'}"]
    if head.get("oid"):
        parts.append(f"head_oid={str(head['oid'])[:12]}")
    if head.get("ref"):
        parts.append(f"head_ref={head['ref']}")
    parts.append(f"tracked_changes={dirty_state.get('tracked_change_count', 0)}")
    parts.append(f"untracked={dirty_state.get('untracked_count', 0)}")
    parts.append(f"paths={len(affected_paths)}")
    return " ".join(parts)


def _limited_evidence_refs(evidence_refs: object) -> dict[str, object]:
    if not isinstance(evidence_refs, dict):
        return {}
    filtered = {}
    for key in ("bundle_dir", "metadata_json", "head_ref", "git_diff_stat", "git_diff_cached_stat"):
        value = evidence_refs.get(key)
        if value is not None:
            filtered[key] = value
    return filtered


def _checkpoint_evidence(
    checkpoint: dict[str, object] | None,
    *,
    task_id: str,
    decision_event_id: str | None,
) -> dict[str, object] | None:
    if not isinstance(checkpoint, dict):
        return None
    linked_decision_event_id = str(decision_event_id or checkpoint.get("decision_event_id") or "") or None
    return {
        "status": "decision_linked" if linked_decision_event_id else "recorded",
        "task_id": task_id,
        "checkpoint_id": checkpoint.get("checkpoint_id"),
        "target_action": checkpoint.get("target_action"),
        "actor_id": checkpoint.get("actor_id"),
        "captured_at": checkpoint.get("captured_at"),
        "event_id": checkpoint.get("event_id"),
        "decision_event_id": linked_decision_event_id,
        "baseline_summary": _checkpoint_baseline_summary(checkpoint.get("baseline_fingerprint")),
        "evidence_refs": _limited_evidence_refs(checkpoint.get("evidence_refs")),
    }


def _decision_event_summary(decision_event: dict[str, object] | None) -> dict[str, object] | None:
    if not isinstance(decision_event, dict):
        return None
    return {
        "event_id": decision_event.get("event_id"),
        "event_type": decision_event.get("event_type"),
        "actor_id": decision_event.get("actor_id"),
        "decision_action": decision_event.get("decision_action"),
        "checkpoint_id": decision_event.get("checkpoint_id"),
        "intervention_rationale": decision_event.get("intervention_rationale"),
    }


def _collect_surface_ids(
    version_evidence: dict[str, object] | None,
    secret_evidence: dict[str, object] | None,
) -> list[str]:
    surface_ids = {
        str(result.get("surface_id"))
        for result in (version_evidence or {}).get("surface_results", [])
        if isinstance(result, dict) and result.get("surface_id")
    }
    surface_ids.update(
        {
            str(result.get("surface_id"))
            for result in (secret_evidence or {}).get("surface_results", [])
            if isinstance(result, dict) and result.get("surface_id")
        }
    )
    return sorted(surface_ids)


def _governance_policy_trace(
    state_db: Path,
    *,
    workflow_class: str | None,
    adapter_id: str | None,
    surface_ids: list[str],
    routing_decision: dict[str, object] | None,
    governance: dict[str, object] | None,
) -> dict[str, object] | None:
    orchestration_dir = state_db.parent
    policy_path = governance_policy_path(orchestration_dir)
    try:
        live_policy = load_governance_policy(policy_path, persist_sanitized=False)
    except FileNotFoundError:
        return None
    snapshot = active_governance_snapshot(
        state_db,
        live_policy=live_policy,
        workflow_class=workflow_class,
        adapter_id=adapter_id,
        surface_ids=surface_ids or None,
    )
    rationale = (routing_decision or {}).get("rationale")
    policy_version = (
        (rationale.get("governance_policy_version") if isinstance(rationale, dict) else None)
        or (governance or {}).get("policy_version")
        or live_policy.get("policy_version")
    )
    return {
        "policy_version": policy_version,
        "policy_path": str(policy_path),
        "snapshot": (
            {
                "snapshot_id": snapshot.get("snapshot_id"),
                "traceability_status": snapshot.get("traceability_status"),
                "matches_live_policy": snapshot.get("matches_live_policy"),
            }
            if isinstance(snapshot, dict)
            else None
        ),
    }


def summarize_governance_evidence(
    state_db: Path,
    *,
    task: dict[str, object] | None = None,
    event: dict[str, object] | None = None,
    governance: dict[str, object] | None = None,
) -> dict[str, object] | None:
    task_id = None
    if isinstance(task, dict):
        task_id = str(task.get("task_id") or "")
    if not task_id and isinstance(event, dict):
        if str(event.get("aggregate_type") or "") == "task":
            task_id = str(event.get("aggregate_id") or "")
        else:
            affected_refs = event.get("affected_refs")
            if isinstance(affected_refs, dict):
                task_id = str(affected_refs.get("task_id") or "")
        payload = event.get("payload")
        if not task_id and isinstance(payload, dict):
            task_id = str(payload.get("task_id") or "")
    if not task_id:
        return None

    workflow_class = (
        str(task.get("workflow_class") or "") if isinstance(task, dict) and task.get("workflow_class") else None
    ) or _inspect_task_workflow_class(state_db, task_id)
    routing_decision = (
        task.get("routing_decision") if isinstance(task, dict) and isinstance(task.get("routing_decision"), dict) else None
    ) or _inspect_latest_routing_decision(state_db, task_id)
    task_events = _list_task_events_with_payload(state_db, task_id, limit=None)
    routing_decision_id = str((routing_decision or {}).get("decision_id") or "") or None
    routing_related_event = (
        _match_task_event(task_events, payload_key="routing_decision_id", expected_value=routing_decision_id)
        if routing_decision_id
        else None
    ) or _match_task_event(task_events, event_type="routing.decision_recorded")
    routing_related_event_id = str((routing_related_event or {}).get("event_id") or "") or None

    secret_resolution = None
    if isinstance(event, dict):
        payload = event.get("payload")
        if isinstance(payload, dict) and isinstance(payload.get("secret_resolution"), dict):
            secret_resolution = payload.get("secret_resolution")
    if secret_resolution is None and isinstance(task, dict) and isinstance(task.get("secret_resolution"), dict):
        secret_resolution = task.get("secret_resolution")
    if secret_resolution is None:
        rationale = (routing_decision or {}).get("rationale")
        if isinstance(rationale, dict) and isinstance(rationale.get("secret_resolution"), dict):
            secret_resolution = rationale.get("secret_resolution")

    decision_event = None
    if isinstance(event, dict) and str(event.get("event_type") or "") == "intervention.decision_recorded":
        decision_event = event
    if decision_event is None:
        decision_event = inspect_decision_event(
            state_db,
            str((event or {}).get("decision_event_id") or ""),
        )

    event_checkpoint = checkpoint_for_ref(state_db, event) if isinstance(event, dict) else None
    checkpoint = event_checkpoint
    if checkpoint is None and not isinstance(event, dict):
        checkpoint = latest_task_checkpoint(state_db, task_id)
    if decision_event is None and isinstance(checkpoint, dict) and (
        not isinstance(event, dict) or event_checkpoint is not None
    ):
        decision_event = inspect_decision_event(state_db, str(checkpoint.get("decision_event_id") or ""))

    version_evidence = _surface_version_evidence(governance, routing_decision, related_event_id=routing_related_event_id)
    secret_evidence = _secret_scope_evidence(
        secret_resolution,
        routing_decision_id=routing_decision_id,
        related_event_id=routing_related_event_id,
    )
    checkpoint_evidence = _checkpoint_evidence(
        checkpoint,
        task_id=task_id,
        decision_event_id=str((decision_event or {}).get("event_id") or ""),
    )
    decision_summary = _decision_event_summary(decision_event)

    selected_worker_id = str((routing_decision or {}).get("selected_worker_id") or "") or None
    adapter_id = None
    if version_evidence:
        for result in version_evidence.get("surface_results", []):
            if isinstance(result, dict):
                selector_context = result.get("selector_context")
                if isinstance(selector_context, dict) and selector_context.get("adapter_id"):
                    adapter_id = str(selector_context["adapter_id"])
                    break
    if adapter_id is None and isinstance(secret_resolution, dict) and secret_resolution.get("adapter_id"):
        adapter_id = str(secret_resolution["adapter_id"])
    policy_trace = _governance_policy_trace(
        state_db,
        workflow_class=workflow_class,
        adapter_id=adapter_id,
        surface_ids=_collect_surface_ids(version_evidence, secret_evidence),
        routing_decision=routing_decision,
        governance=governance,
    )

    evidence: dict[str, object] = {"task_id": task_id}
    if policy_trace is not None:
        evidence["policy"] = policy_trace
    if isinstance(routing_decision, dict):
        evidence["routing"] = {
            "decision_id": routing_decision.get("decision_id"),
            "selected_worker_id": selected_worker_id or "none",
            "created_at": routing_decision.get("created_at"),
            "related_event_id": routing_related_event_id,
        }
    if version_evidence is not None:
        evidence["version_pins"] = version_evidence
    if secret_evidence is not None:
        evidence["secret_scope"] = secret_evidence
    if checkpoint_evidence is not None:
        evidence["checkpoint"] = checkpoint_evidence
    if decision_summary is not None:
        evidence["decision_event"] = decision_summary

    if not any(key in evidence for key in ("routing", "version_pins", "secret_scope", "checkpoint", "decision_event")):
        return None
    return evidence
