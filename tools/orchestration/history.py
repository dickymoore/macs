#!/usr/bin/env python3
"""Lease and event inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path

from tools.orchestration.store import connect_state_db


class ObjectNotFoundError(RuntimeError):
    """Raised when an inspected object does not exist."""


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
    return [dict(row) for row in rows]


def list_events(state_db: Path) -> list[dict[str, object]]:
    conn = connect_state_db(state_db)
    try:
        rows = conn.execute(
            """
            SELECT event_id, event_type, aggregate_type, aggregate_id, timestamp, actor_type, actor_id, payload
            FROM events
            ORDER BY timestamp, event_id
            """
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        items.append(
            {
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "aggregate_type": row["aggregate_type"],
                "aggregate_id": row["aggregate_id"],
                "timestamp": row["timestamp"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "payload_summary": json.loads(row["payload"]),
            }
        )
    return items


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
    item = dict(row)
    item["payload"] = json.loads(item["payload"])
    return item
