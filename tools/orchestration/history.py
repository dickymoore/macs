#!/usr/bin/env python3
"""Lease and event inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path

from tools.orchestration.store import connect_state_db


class ObjectNotFoundError(RuntimeError):
    """Raised when an inspected object does not exist."""


def _load_payload(raw_payload: str | None) -> dict[str, object]:
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
