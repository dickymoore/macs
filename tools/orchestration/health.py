#!/usr/bin/env python3
"""Worker health classification helpers."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.store import EventRecord, connect_state_db, write_eventful_transaction
from tools.orchestration.workers import MANUAL_DISABLE_TAG, list_workers


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def classify_workers(state_db: Path, events_ndjson: Path) -> list[dict[str, object]]:
    workers = list_workers(state_db)
    changes = []
    for worker in workers:
        next_state = classify_worker_state(worker)
        if next_state != worker["state"]:
            apply_worker_state(state_db, events_ndjson, worker, next_state)
            changes.append({"worker_id": worker["worker_id"], "previous_state": worker["state"], "next_state": next_state})
    return changes


def classify_worker_state(worker: dict[str, object]) -> str:
    if worker["state"] == "quarantined":
        return "quarantined"
    if MANUAL_DISABLE_TAG in worker["operator_tags"]:
        return "unavailable"
    freshness = worker["freshness_seconds"]
    if freshness > 600:
        return "unavailable"
    if freshness > 60:
        return "degraded"
    if worker["state"] in {"ready", "busy", "degraded", "unavailable"}:
        return "ready" if worker["state"] != "busy" else "busy"
    return worker["state"]


def apply_worker_state(state_db: Path, events_ndjson: Path, worker: dict[str, object], next_state: str) -> None:
    timestamp = utc_now()
    event = EventRecord(
        event_id=f"evt-worker-health-{uuid.uuid4().hex[:12]}",
        event_type="worker.health_reclassified",
        aggregate_type="worker",
        aggregate_id=worker["worker_id"],
        timestamp=timestamp,
        actor_type="controller",
        actor_id="controller-main",
        correlation_id=f"corr-worker-health-{uuid.uuid4().hex[:12]}",
        causation_id=None,
        payload={
            "previous_state": worker["state"],
            "next_state": next_state,
            "freshness_seconds": worker["freshness_seconds"],
        },
        redaction_level="none",
    )

    def mutator(conn) -> None:
        conn.execute("UPDATE workers SET state = ? WHERE worker_id = ?", (next_state, worker["worker_id"]))

    write_eventful_transaction(state_db, events_ndjson, event, mutator)
