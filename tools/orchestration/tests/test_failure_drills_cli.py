#!/usr/bin/env python3
"""tmux-backed failure drill coverage for mandatory orchestration failure classes."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.orchestration.invariants import LeaseRecord, TaskRecord, create_task, issue_lease, transition_task_state
from tools.orchestration.store import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = [sys.executable, "-m", "tools.orchestration.cli.main"]


class FailureDrillCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-failure-drill-test-"))
        self.repo_root = self.temp_dir / "repo"
        self.repo_root.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + self.env.get("PYTHONPATH", "")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def run_cli(
        self,
        *args: str,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = self.env.copy()
        if env_overrides:
            for key, value in env_overrides.items():
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value
        return subprocess.run(
            CLI + ["--repo", str(self.repo_root), *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def iso_now(self, *, seconds_ago: int = 0) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).replace(microsecond=0).isoformat()

    def init_repo(self) -> None:
        result = self.run_cli("setup", "init")
        self.assertEqual(result.returncode, 0, result.stderr)

    def start_tmux_worker(self, name: str) -> tuple[str, str, str]:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")
        tmux_dir = self.temp_dir / f"tmux-{name}"
        tmux_dir.mkdir(exist_ok=True)
        socket = tmux_dir / f"{name}.sock"
        session = f"macs-failure-{name}-{os.getpid()}"
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", "worker"],
            check=True,
            capture_output=True,
            text=True,
        )
        pane_id = subprocess.run(
            ["tmux", "-S", str(socket), "list-panes", "-t", session, "-F", "#{pane_id}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        return str(socket), session, pane_id

    def seed_worker_row(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        adapter_id: str,
        tmux_socket: str,
        tmux_session: str,
        tmux_pane: str,
        capabilities: list[str] | None = None,
        operator_tags: list[str] | None = None,
        state: str = "ready",
    ) -> str:
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
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
                    adapter_id,
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
                    state,
                    json.dumps(capabilities or ["implementation"]),
                    "required_only",
                    self.iso_now(),
                    self.iso_now(),
                    "interruptible",
                    json.dumps(operator_tags or ["registered"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id

    def seed_task(
        self,
        *,
        task_id: str,
        summary: str,
        workflow_class: str = "implementation",
        protected_surfaces: list[str] | None = None,
    ) -> str:
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        create_task(
            orchestration_dir / "state.db",
            orchestration_dir / "events.ndjson",
            TaskRecord(
                task_id=task_id,
                title=summary,
                description=summary,
                workflow_class=workflow_class,
                intent=summary,
                required_capabilities=[],
                protected_surfaces=protected_surfaces or [],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id=f"evt-task-seed-{task_id}",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id=task_id,
                timestamp=self.iso_now(seconds_ago=10),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-task-seed-{task_id}",
                causation_id=None,
                payload={"summary": summary, "workflow_class": workflow_class},
                redaction_level="none",
            ),
        )
        return task_id

    def update_worker_operator_tags(self, worker_id: str, operator_tags: list[str]) -> None:
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                "UPDATE workers SET operator_tags = ? WHERE worker_id = ?",
                (json.dumps(operator_tags), worker_id),
            )
            conn.commit()
        finally:
            conn.close()

    def update_worker_freshness(self, worker_id: str, *, seconds_ago: int) -> None:
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                UPDATE workers
                SET last_evidence_at = ?, last_heartbeat_at = ?
                WHERE worker_id = ?
                """,
                (self.iso_now(seconds_ago=seconds_ago), self.iso_now(seconds_ago=seconds_ago), worker_id),
            )
            conn.commit()
        finally:
            conn.close()

    def seed_active_task_with_lease_and_lock(
        self,
        *,
        task_id: str,
        lease_id: str,
        worker_id: str,
        tmux_socket: str,
        tmux_session: str,
        tmux_pane: str,
        protected_surface: str,
    ) -> tuple[str, str]:
        self.seed_worker_row(
            worker_id=worker_id,
            runtime_type="codex",
            adapter_id="codex",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            capabilities=["implementation", "review"],
        )
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        self.seed_task(
            task_id=task_id,
            summary=f"Failure drill for {task_id}",
            protected_surfaces=[protected_surface],
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute("UPDATE tasks SET state = 'reserved' WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id=lease_id,
                task_id=task_id,
                worker_id=worker_id,
                state="active",
                issued_at=self.iso_now(seconds_ago=5),
                accepted_at=self.iso_now(seconds_ago=4),
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version=f"evidence-{task_id}",
            ),
            EventRecord(
                event_id=f"evt-lease-{lease_id}",
                event_type="lease.activated",
                aggregate_type="lease",
                aggregate_id=lease_id,
                timestamp=self.iso_now(seconds_ago=4),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-lease-{lease_id}",
                causation_id=None,
                payload={"task_id": task_id, "worker_id": worker_id},
                redaction_level="none",
            ),
        )
        transition_task_state(
            state_db,
            events_ndjson,
            task_id,
            "active",
            EventRecord(
                event_id=f"evt-task-active-{task_id}",
                event_type="task.activated",
                aggregate_type="task",
                aggregate_id=task_id,
                timestamp=self.iso_now(seconds_ago=3),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-task-active-{task_id}",
                causation_id=None,
                payload={"task_id": task_id, "lease_id": lease_id},
                redaction_level="none",
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"lock-{task_id}",
                    "file",
                    protected_surface,
                    "exclusive_write",
                    "active",
                    task_id,
                    lease_id,
                    "phase1-defaults-v1",
                    self.iso_now(seconds_ago=2),
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return task_id, lease_id

    def seed_interrupted_recovery_task(
        self,
        *,
        task_id: str,
        recovery_run_id: str,
        proposed_worker_id: str,
    ) -> tuple[str, str]:
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id=task_id,
                title="Interrupted recovery drill",
                description="Interrupted recovery drill",
                workflow_class="implementation",
                intent="Interrupted recovery drill",
                required_capabilities=[],
                protected_surfaces=["docs/interrupted-recovery-drill.md"],
                priority="normal",
                state="reconciliation",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref="phase1-defaults-v1",
            ),
            EventRecord(
                event_id=f"evt-task-seed-{task_id}",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id=task_id,
                timestamp=self.iso_now(seconds_ago=30),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-task-seed-{task_id}",
                causation_id=None,
                payload={"summary": "Interrupted recovery drill"},
                redaction_level="none",
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO recovery_runs (
                    recovery_run_id, task_id, state, started_at, ended_at, anomaly_summary, decision_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recovery_run_id,
                    task_id,
                    "pending_retry",
                    self.iso_now(seconds_ago=10),
                    None,
                    json.dumps(
                        {
                            "kind": "ambiguous_ownership",
                            "basis": "worker_state_unavailable",
                            "predecessor_worker_id": "worker-predecessor",
                            "predecessor_lease_id": "lease-predecessor",
                        },
                        sort_keys=True,
                    ),
                    json.dumps(
                        {
                            "allowed_next_actions": [
                                f"macs recovery retry --task {task_id}",
                                f"macs recovery reconcile --task {task_id}",
                            ],
                            "proposed_worker_id": proposed_worker_id,
                            "proposed_workflow_class": "implementation",
                            "recommended_action": "retry",
                            "recovery_phase": "predecessor_revoked",
                        },
                        sort_keys=True,
                    ),
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return task_id, recovery_run_id

    def count_live_leases(self, task_id: str) -> int:
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            return conn.execute(
                """
                SELECT COUNT(*)
                FROM leases
                WHERE task_id = ? AND state IN ('pending_accept', 'active', 'paused', 'suspended', 'expiring')
                """,
                (task_id,),
            ).fetchone()[0]
        finally:
            conn.close()

    def seed_split_brain_task(
        self,
        *,
        task_id: str,
        first_lease_id: str,
        second_lease_id: str,
        first_worker_id: str,
        second_worker_id: str,
        first_tmux: tuple[str, str, str],
        second_tmux: tuple[str, str, str],
    ) -> None:
        self.seed_active_task_with_lease_and_lock(
            task_id=task_id,
            lease_id=first_lease_id,
            worker_id=first_worker_id,
            tmux_socket=first_tmux[0],
            tmux_session=first_tmux[1],
            tmux_pane=first_tmux[2],
            protected_surface="docs/split-brain-drill.md",
        )
        self.seed_worker_row(
            worker_id=second_worker_id,
            runtime_type="codex",
            adapter_id="codex",
            tmux_socket=second_tmux[0],
            tmux_session=second_tmux[1],
            tmux_pane=second_tmux[2],
            capabilities=["implementation"],
        )
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute("DROP INDEX IF EXISTS idx_one_live_lease_per_task")
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, task_id, worker_id, state, issued_at, accepted_at,
                    ended_at, replacement_lease_id, intervention_reason, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    second_lease_id,
                    task_id,
                    second_worker_id,
                    "active",
                    self.iso_now(seconds_ago=2),
                    self.iso_now(seconds_ago=1),
                    None,
                    None,
                    None,
                    "evidence-split-brain",
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_worker_disconnect_discovery_marks_worker_unavailable_and_freezes_active_task(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("disconnect-owner")
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-disconnect",
            lease_id="lease-failure-disconnect",
            worker_id="worker-failure-disconnect",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            protected_surface="docs/disconnect-drill.md",
        )

        subprocess.run(
            ["tmux", "-S", tmux_socket, "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )

        discover_result = self.run_cli(
            "worker",
            "discover",
            "--tmux-socket",
            tmux_socket,
            "--tmux-session",
            tmux_session,
            "--json",
        )
        self.assertEqual(discover_result.returncode, 0, discover_result.stdout + discover_result.stderr)

        worker_list_payload = json.loads(self.run_cli("worker", "list", "--json").stdout)
        worker = next(item for item in worker_list_payload["data"]["workers"] if item["worker_id"] == "worker-failure-disconnect")
        self.assertEqual(worker["state"], "unavailable")

        task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(task_payload["task"]["current_lease_id"], lease_id)
        self.assertEqual(task_payload["task"]["controller_truth"]["current_lease"]["state"], "suspended")

        event_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_payload["data"]["events"]]
        self.assertIn("lease.suspended", event_types)
        self.assertIn("task.risk_hold_applied", event_types)

    def test_budget_exhaustion_signal_degrades_worker_and_preserves_signal_in_event_trail(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("budget-owner")
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-budget",
            lease_id="lease-failure-budget",
            worker_id="worker-failure-budget",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            protected_surface="docs/budget-drill.md",
        )
        self.update_worker_operator_tags("worker-failure-budget", ["registered", "signal:budget_exhausted"])

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stdout + overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        self.assertEqual(overview_payload["data"]["health_changes"][0]["next_state"], "degraded")
        self.assertEqual(overview_payload["data"]["health_changes"][0]["frozen_task_ids"], [task_id])

        task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(task_payload["task"]["controller_truth"]["current_owner"]["state"], "degraded")
        self.assertEqual(task_payload["task"]["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(task_payload["task"]["current_lease_id"], lease_id)

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        reclassify_event = next(
            item for item in event_list_payload["data"]["events"] if item["event_type"] == "worker.health_reclassified"
        )
        inspect_payload = json.loads(self.run_cli("event", "inspect", "--event", reclassify_event["event_id"], "--json").stdout)
        self.assertIn("signal:budget_exhausted", inspect_payload["data"]["event"]["payload"]["operator_tags"])

    def test_misleading_health_signal_degrades_worker_and_freezes_owned_task(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("misleading-owner")
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-misleading-health",
            lease_id="lease-failure-misleading-health",
            worker_id="worker-failure-misleading-health",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            protected_surface="docs/misleading-health-drill.md",
        )
        self.update_worker_operator_tags("worker-failure-misleading-health", ["registered", "signal:misleading_health"])

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stdout + overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        self.assertEqual(overview_payload["data"]["health_changes"][0]["next_state"], "degraded")

        task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(task_payload["task"]["controller_truth"]["current_owner"]["state"], "degraded")

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("worker.health_reclassified", event_types)
        self.assertIn("lease.suspended", event_types)
        self.assertIn("task.risk_hold_applied", event_types)

    def test_stale_divergence_freezes_owned_task_without_successor_lease(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("stale-owner")
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-stale",
            lease_id="lease-failure-stale",
            worker_id="worker-failure-stale",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            protected_surface="docs/stale-drill.md",
        )
        self.update_worker_freshness("worker-failure-stale", seconds_ago=180)

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stdout + overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        self.assertEqual(overview_payload["data"]["health_changes"][0]["next_state"], "degraded")
        self.assertEqual(overview_payload["data"]["health_changes"][0]["frozen_task_ids"], [task_id])

        task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(task_payload["task"]["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(task_payload["task"]["current_lease_id"], lease_id)
        self.assertEqual(self.count_live_leases(task_id), 1)

    def test_duplicate_claim_is_blocked_without_creating_second_live_lease(self) -> None:
        self.init_repo()
        owner_tmux = self.start_tmux_worker("duplicate-owner")
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-duplicate",
            lease_id="lease-failure-duplicate",
            worker_id="worker-failure-duplicate-owner",
            tmux_socket=owner_tmux[0],
            tmux_session=owner_tmux[1],
            tmux_pane=owner_tmux[2],
            protected_surface="docs/duplicate-drill.md",
        )
        contender_tmux = self.start_tmux_worker("duplicate-successor")
        self.seed_worker_row(
            worker_id="worker-failure-duplicate-successor",
            runtime_type="codex",
            adapter_id="codex",
            tmux_socket=contender_tmux[0],
            tmux_session=contender_tmux[1],
            tmux_pane=contender_tmux[2],
            capabilities=["implementation"],
        )

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-failure-duplicate-successor",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertEqual(self.count_live_leases(task_id), 1)

        task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(task_payload["task"]["state"], "active")
        self.assertEqual(task_payload["task"]["current_worker_id"], "worker-failure-duplicate-owner")

        event_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        duplicate_lease_events = [
            item for item in event_payload["data"]["events"] if item["event_type"] == "lease.activated"
        ]
        self.assertEqual(len(duplicate_lease_events), 1)

    def test_split_brain_startup_recovery_suspends_conflicting_live_leases_and_blocks_progress(self) -> None:
        self.init_repo()
        first_tmux = self.start_tmux_worker("split-brain-a")
        second_tmux = self.start_tmux_worker("split-brain-b")
        self.seed_split_brain_task(
            task_id="task-failure-split-brain",
            first_lease_id="lease-failure-split-brain-a",
            second_lease_id="lease-failure-split-brain-b",
            first_worker_id="worker-failure-split-brain-a",
            second_worker_id="worker-failure-split-brain-b",
            first_tmux=first_tmux,
            second_tmux=second_tmux,
        )

        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["data"]["startup_summary"]
        self.assertTrue(summary["assignments_blocked"])
        self.assertEqual(summary["unresolved_anomalies"]["tasks_pending_reconciliation"], ["task-failure-split-brain"])
        self.assertEqual(
            sorted(summary["unresolved_anomalies"]["suspended_lease_ids"]),
            ["lease-failure-split-brain-a", "lease-failure-split-brain-b"],
        )

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            suspended = conn.execute(
                """
                SELECT lease_id, state
                FROM leases
                WHERE task_id = ?
                ORDER BY lease_id
                """,
                ("task-failure-split-brain",),
            ).fetchall()
        finally:
            conn.close()
        self.assertEqual(
            suspended,
            [("lease-failure-split-brain-a", "suspended"), ("lease-failure-split-brain-b", "suspended")],
        )

        event_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        self.assertIn(
            "controller.startup_recovery_completed",
            [item["event_type"] for item in event_payload["data"]["events"]],
        )

    def test_lock_collision_blocks_conflicting_assignment_while_preserving_existing_lock_history(self) -> None:
        self.init_repo()
        owner_tmux = self.start_tmux_worker("lock-owner")
        self.seed_active_task_with_lease_and_lock(
            task_id="task-failure-lock-owner",
            lease_id="lease-failure-lock-owner",
            worker_id="worker-failure-lock-owner",
            tmux_socket=owner_tmux[0],
            tmux_session=owner_tmux[1],
            tmux_pane=owner_tmux[2],
            protected_surface="docs/lock-drill.md",
        )
        contender_tmux = self.start_tmux_worker("lock-contender")
        self.seed_worker_row(
            worker_id="worker-failure-lock-contender",
            runtime_type="codex",
            adapter_id="codex",
            tmux_socket=contender_tmux[0],
            tmux_session=contender_tmux[1],
            tmux_pane=contender_tmux[2],
            capabilities=["implementation"],
        )
        self.seed_task(
            task_id="task-failure-lock-contender",
            summary="Lock collision contender",
            protected_surfaces=["docs/lock-drill.md"],
        )

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            "task-failure-lock-contender",
            "--worker",
            "worker-failure-lock-contender",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "conflict")

        contender_payload = json.loads(
            self.run_cli("task", "inspect", "--task", "task-failure-lock-contender", "--json").stdout
        )
        self.assertEqual(contender_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(contender_payload["task"]["current_lease_id"])

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(len(lock_payload["data"]["locks"]), 1)
        self.assertEqual(lock_payload["data"]["locks"][0]["task_id"], "task-failure-lock-owner")

        event_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        self.assertFalse(
            any(
                item["aggregate_id"] == "task-failure-lock-contender" and item["event_type"] == "task.assigned"
                for item in event_payload["data"]["events"]
            )
        )

    def test_interrupted_recovery_retry_keeps_successor_assignment_blocked_until_retry_completes(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("recovery-target")
        self.seed_worker_row(
            worker_id="worker-failure-recovery-target",
            runtime_type="codex",
            adapter_id="codex",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
            capabilities=["implementation"],
        )
        task_id, recovery_run_id = self.seed_interrupted_recovery_task(
            task_id="task-failure-interrupted-recovery",
            recovery_run_id="recovery-failure-interrupted-recovery",
            proposed_worker_id="worker-failure-recovery-target",
        )

        assign_result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-failure-recovery-target",
            "--json",
        )
        self.assertEqual(assign_result.returncode, 5, assign_result.stdout + assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertEqual(assign_payload["errors"][0]["code"], "degraded_precondition")
        self.assertIn(recovery_run_id, assign_payload["errors"][0]["message"])

        retry_result = self.run_cli("recovery", "retry", "--task", task_id, "--confirm", "--json")
        self.assertEqual(retry_result.returncode, 0, retry_result.stdout + retry_result.stderr)
        retry_payload = json.loads(retry_result.stdout)
        self.assertEqual(retry_payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(retry_payload["data"]["result"]["task"]["current_worker_id"], "worker-failure-recovery-target")
        self.assertEqual(retry_payload["data"]["recovery_run"]["state"], "completed")

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("recovery.retry_requested", event_types)
        self.assertIn("task.assigned", event_types)


if __name__ == "__main__":
    unittest.main()
