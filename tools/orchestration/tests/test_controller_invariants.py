#!/usr/bin/env python3
"""Deterministic unit tests for controller state invariants."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.orchestration.invariants import (
    InvariantViolationError,
    LeaseRecord,
    TaskRecord,
    create_task,
    issue_lease,
    transition_task_state,
)
from tools.orchestration.locks import check_lock_conflicts
from tools.orchestration.recovery import inspect_recovery_context
from tools.orchestration.routing import evaluate_task_routing
from tools.orchestration.session import ensure_orchestration_store
from tools.orchestration.store import EventRecord, connect_state_db


class ControllerInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name)
        self.paths, _, _, _ = ensure_orchestration_store(self.repo_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def iso_now(self, *, seconds_ago: int = 0) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).replace(microsecond=0).isoformat()

    def event(
        self,
        *,
        event_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict[str, object] | None = None,
    ) -> EventRecord:
        return EventRecord(
            event_id=event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            timestamp=self.iso_now(),
            actor_type="controller",
            actor_id="controller-main",
            correlation_id=f"corr-{event_id}",
            causation_id=None,
            payload=payload or {},
            redaction_level="none",
        )

    def seed_task(self, *, task_id: str, workflow_class: str = "implementation") -> None:
        create_task(
            self.paths.state_db,
            self.paths.events_ndjson,
            TaskRecord(
                task_id=task_id,
                title=task_id,
                description=task_id,
                workflow_class=workflow_class,
                intent=task_id,
                required_capabilities=[workflow_class] if workflow_class != "implementation" else ["implementation"],
                protected_surfaces=[],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            self.event(
                event_id=f"evt-{task_id}-created",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id=task_id,
                payload={"task_id": task_id},
            ),
        )

    def insert_worker(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        state: str = "ready",
        capabilities: list[str] | None = None,
        freshness_seconds: int = 5,
        interruptibility: str = "interruptible",
    ) -> None:
        conn = connect_state_db(self.paths.state_db)
        try:
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    worker_id,
                    runtime_type,
                    runtime_type,
                    "/tmp/test.sock",
                    "test",
                    "%1",
                    state,
                    json.dumps(capabilities or [runtime_type]),
                    "required_only",
                    self.iso_now(seconds_ago=freshness_seconds),
                    self.iso_now(seconds_ago=freshness_seconds),
                    interruptibility,
                    json.dumps(["registered"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_issue_lease_rejects_second_live_lease_for_same_task(self) -> None:
        self.seed_task(task_id="task-live-lease")

        issue_lease(
            self.paths.state_db,
            self.paths.events_ndjson,
            LeaseRecord(
                lease_id="lease-live-1",
                task_id="task-live-lease",
                worker_id="worker-a",
                state="active",
                issued_at=self.iso_now(),
                accepted_at=self.iso_now(),
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="test-v1",
            ),
            self.event(
                event_id="evt-lease-live-1",
                event_type="lease.activated",
                aggregate_type="lease",
                aggregate_id="lease-live-1",
            ),
        )

        with self.assertRaises(InvariantViolationError):
            issue_lease(
                self.paths.state_db,
                self.paths.events_ndjson,
                LeaseRecord(
                    lease_id="lease-live-2",
                    task_id="task-live-lease",
                    worker_id="worker-b",
                    state="active",
                    issued_at=self.iso_now(),
                    accepted_at=self.iso_now(),
                    ended_at=None,
                    replacement_lease_id=None,
                    intervention_reason=None,
                    evidence_version="test-v1",
                ),
                self.event(
                    event_id="evt-lease-live-2",
                    event_type="lease.activated",
                    aggregate_type="lease",
                    aggregate_id="lease-live-2",
                ),
            )

    def test_transition_task_state_rejects_activation_without_live_lease(self) -> None:
        self.seed_task(task_id="task-no-lease")

        with self.assertRaises(InvariantViolationError):
            transition_task_state(
                self.paths.state_db,
                self.paths.events_ndjson,
                "task-no-lease",
                "active",
                self.event(
                    event_id="evt-task-no-lease-active",
                    event_type="task.activated",
                    aggregate_type="task",
                    aggregate_id="task-no-lease",
                ),
            )

    def test_check_lock_conflicts_detects_directory_file_overlap(self) -> None:
        conn = connect_state_db(self.paths.state_db)
        try:
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-dir-1",
                    "directory",
                    "docs/architecture",
                    "exclusive_write",
                    "active",
                    "task-lock-owner",
                    "lease-lock-owner",
                    "policy",
                    self.iso_now(),
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        conflict = check_lock_conflicts(self.paths.state_db, ["docs/architecture/decision.md"])
        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["conflicts"][0]["conflicting_lock_id"], "lock-dir-1")
        self.assertEqual(conflict["conflicts"][0]["conflicting_surface_ref"], "docs/architecture/")

    def test_evaluate_task_routing_rejects_stale_worker_and_selects_fresh_candidate(self) -> None:
        self.insert_worker(
            worker_id="worker-codex-stale",
            runtime_type="codex",
            capabilities=["implementation"],
            freshness_seconds=120,
        )
        self.insert_worker(
            worker_id="worker-claude-fresh",
            runtime_type="claude",
            capabilities=["implementation"],
            freshness_seconds=5,
        )

        evaluation = evaluate_task_routing(
            self.repo_root,
            self.paths.state_db,
            {
                "task_id": "task-route",
                "workflow_class": "implementation",
                "required_capabilities": ["implementation"],
            },
        )

        self.assertEqual(evaluation.selected_worker_id, "worker-claude-fresh")
        stale_rejection = next(item for item in evaluation.rejected_workers if item["worker_id"] == "worker-codex-stale")
        self.assertIn("stale_evidence", stale_rejection["reasons"])

    def test_inspect_recovery_context_reports_interrupted_retry_without_live_lease(self) -> None:
        self.seed_task(task_id="task-recovery", workflow_class="implementation")
        conn = connect_state_db(self.paths.state_db)
        try:
            conn.execute(
                """
                UPDATE tasks
                SET state = 'reconciliation', routing_policy_ref = ?
                WHERE task_id = ?
                """,
                ("phase1-defaults-v1", "task-recovery"),
            )
            conn.execute(
                """
                INSERT INTO recovery_runs (
                    recovery_run_id, task_id, state, started_at, ended_at, anomaly_summary, decision_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "recovery-task-retry",
                    "task-recovery",
                    "pending_retry",
                    self.iso_now(),
                    None,
                    json.dumps({"kind": "ambiguous_ownership"}, sort_keys=True),
                    json.dumps(
                        {
                            "recommended_action": "retry",
                            "allowed_next_actions": ["macs recovery retry --task task-recovery"],
                        },
                        sort_keys=True,
                    ),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        recovery = inspect_recovery_context(self.paths.state_db, task_id="task-recovery")
        self.assertEqual(recovery["recovery_run"]["state"], "pending_retry")
        self.assertEqual(recovery["blocking_condition"], "interrupted recovery run is blocking successor routing")
        self.assertEqual(recovery["next_action"], "macs recovery retry --task task-recovery")


if __name__ == "__main__":
    unittest.main()
