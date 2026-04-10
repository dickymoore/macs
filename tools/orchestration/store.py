#!/usr/bin/env python3
"""SQLite-backed authoritative state and NDJSON event export."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tools.orchestration.state_machine import LEASE_STATES, LIVE_LEASE_STATES, TASK_STATES


SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class StoreBootstrapResult:
    state_db_created: bool
    events_ndjson_created: bool


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    timestamp: str
    actor_type: str
    actor_id: str
    correlation_id: str
    causation_id: str | None
    payload: dict[str, object]
    redaction_level: str

    def as_row(self) -> tuple[str, str, str, str, str, str, str, str, str | None, str, str]:
        return (
            self.event_id,
            self.event_type,
            self.aggregate_type,
            self.aggregate_id,
            self.timestamp,
            self.actor_type,
            self.actor_id,
            self.correlation_id,
            self.causation_id,
            json.dumps(self.payload, sort_keys=True),
            self.redaction_level,
        )

    def as_export(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_type": self.aggregate_type,
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
            "redaction_level": self.redaction_level,
        }


def connect_state_db(state_db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(state_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def bootstrap_state_store(state_db: Path, events_ndjson: Path) -> StoreBootstrapResult:
    state_db.parent.mkdir(parents=True, exist_ok=True)
    state_db_created = not state_db.exists()
    events_created = not events_ndjson.exists()

    conn = connect_state_db(state_db)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_schema_sql())
        conn.execute(
            "INSERT OR IGNORE INTO metadata(key, value) VALUES('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        conn.commit()
    finally:
        conn.close()

    events_ndjson.touch(exist_ok=True)
    return StoreBootstrapResult(
        state_db_created=state_db_created,
        events_ndjson_created=events_created,
    )


def append_event_export(events_ndjson: Path, event: EventRecord) -> None:
    with events_ndjson.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.as_export(), sort_keys=True) + "\n")


def write_eventful_transaction(
    state_db: Path,
    events_ndjson: Path,
    event: EventRecord,
    mutator: Callable[[sqlite3.Connection], None],
) -> None:
    conn = connect_state_db(state_db)
    try:
        conn.execute("BEGIN")
        mutator(conn)
        conn.execute(
            """
            INSERT INTO events (
                event_id, event_type, aggregate_type, aggregate_id, timestamp,
                actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            event.as_row(),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    append_event_export(events_ndjson, event)


def _schema_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS workers (
        worker_id TEXT PRIMARY KEY,
        runtime_type TEXT,
        adapter_id TEXT,
        tmux_socket TEXT,
        tmux_session TEXT,
        tmux_pane TEXT,
        state TEXT,
        capabilities TEXT,
        required_signal_status TEXT,
        last_evidence_at TEXT,
        last_heartbeat_at TEXT,
        interruptibility TEXT,
        operator_tags TEXT
    );

    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        workflow_class TEXT,
        intent TEXT,
        required_capabilities TEXT,
        protected_surfaces TEXT,
        priority TEXT,
        state TEXT CHECK(state IN ({})),
        current_worker_id TEXT,
        current_lease_id TEXT,
        routing_policy_ref TEXT
    );

    CREATE TABLE IF NOT EXISTS leases (
        lease_id TEXT PRIMARY KEY,
        task_id TEXT,
        worker_id TEXT,
        state TEXT CHECK(state IN ({})),
        issued_at TEXT,
        accepted_at TEXT,
        ended_at TEXT,
        replacement_lease_id TEXT,
        intervention_reason TEXT,
        evidence_version TEXT
    );

    CREATE TABLE IF NOT EXISTS locks (
        lock_id TEXT PRIMARY KEY,
        target_type TEXT,
        target_ref TEXT,
        mode TEXT,
        state TEXT,
        task_id TEXT,
        lease_id TEXT,
        policy_origin TEXT,
        created_at TEXT,
        released_at TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        event_type TEXT NOT NULL,
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        actor_type TEXT NOT NULL,
        actor_id TEXT NOT NULL,
        correlation_id TEXT NOT NULL,
        causation_id TEXT,
        payload TEXT NOT NULL,
        redaction_level TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS routing_decisions (
        decision_id TEXT PRIMARY KEY,
        task_id TEXT,
        selected_worker_id TEXT,
        rationale TEXT,
        evidence_ref TEXT,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS evidence_records (
        evidence_id TEXT PRIMARY KEY,
        worker_id TEXT,
        source_type TEXT,
        captured_at TEXT,
        freshness_seconds INTEGER,
        payload TEXT,
        confidence TEXT
    );

    CREATE TABLE IF NOT EXISTS recovery_runs (
        recovery_run_id TEXT PRIMARY KEY,
        task_id TEXT,
        state TEXT,
        started_at TEXT,
        ended_at TEXT,
        anomaly_summary TEXT,
        decision_summary TEXT
    );

    CREATE TABLE IF NOT EXISTS policy_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        policy_origin TEXT,
        policy_version TEXT,
        captured_at TEXT,
        payload TEXT
    );

    CREATE UNIQUE INDEX IF NOT EXISTS idx_one_live_lease_per_task
    ON leases(task_id)
    WHERE state IN ({});
    """.format(
        ",".join(f"'{state}'" for state in TASK_STATES),
        ",".join(f"'{state}'" for state in LEASE_STATES),
        ",".join(f"'{state}'" for state in LIVE_LEASE_STATES),
    )
