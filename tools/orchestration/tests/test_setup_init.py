#!/usr/bin/env python3
"""Tests for orchestration bootstrap and controller lock behavior."""

from __future__ import annotations

import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.orchestration.adapters.codex import CodexAdapter
from tools.orchestration.invariants import (
    InvariantViolationError,
    LeaseRecord,
    TaskRecord,
    create_task,
    issue_lease,
    transition_task_state,
    transition_lease_state,
)
from tools.orchestration.store import EventRecord, write_eventful_transaction


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = [sys.executable, "-m", "tools.orchestration.cli.main"]
START_CONTROLLER = REPO_ROOT / "tools" / "tmux_bridge" / "start_controller.sh"


class SetupInitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-orch-test-"))
        self.repo_root = self.temp_dir / "repo"
        self.repo_root.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + self.env.get("PYTHONPATH", "")
        self.env["TMUX_SESSION"] = "macs-test"
        self.env["TMUX_SOCKET"] = "/tmp/macs-test.sock"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            CLI + ["--repo", str(self.repo_root), *args],
            cwd=REPO_ROOT,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def iso_now(self, *, seconds_ago: int = 0) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).replace(microsecond=0).isoformat()

    def test_setup_init_creates_repo_local_layout(self) -> None:
        result = self.run_cli("setup", "init")
        self.assertEqual(result.returncode, 0, result.stderr)

        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        self.assertTrue(orchestration_dir.is_dir())
        self.assertTrue((orchestration_dir / "controller.lock").exists())
        self.assertTrue((orchestration_dir / "state.db").exists())
        self.assertTrue((orchestration_dir / "events.ndjson").exists())

    def test_setup_init_accepts_json_flag_after_subcommand(self) -> None:
        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup init")
        self.assertIn("controller_lock", payload["data"])
        self.assertEqual(payload["data"]["state_db_status"], "created")
        self.assertEqual(payload["data"]["events_ndjson_status"], "created")
        self.assertFalse(payload["data"]["startup_summary"]["assignments_blocked"])

    def test_setup_init_blocks_second_active_controller(self) -> None:
        holder = subprocess.Popen(
            CLI
            + [
                "--repo",
                str(self.repo_root),
                "setup",
                "init",
                "--exec",
                sys.executable,
                "-c",
                "import time; time.sleep(10)",
            ],
            cwd=REPO_ROOT,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            lock_path = self.repo_root / ".codex" / "orchestration" / "controller.lock"
            for _ in range(50):
                if lock_path.exists() and lock_path.read_text(encoding="utf-8").strip():
                    break
                time.sleep(0.1)
            else:
                self.fail("controller lock file was not populated")

            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["repo_root"], str(self.repo_root))
            self.assertIn("pid", payload)

            result = self.run_cli(
                "setup",
                "init",
                "--exec",
                sys.executable,
                "-c",
                "print('second-controller-should-not-start')",
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("Another controller session is already active", result.stderr)
            self.assertIn(str(payload["pid"]), result.stderr)
            self.assertIn("tmux session: macs-test", result.stderr)
        finally:
            holder.send_signal(signal.SIGTERM)
            holder.wait(timeout=5)
            if holder.stdout is not None:
                holder.stdout.close()
            if holder.stderr is not None:
                holder.stderr.close()

    def test_start_controller_launcher_enforces_single_controller_lock(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        tmux_dir = self.temp_dir / "tmux"
        tmux_dir.mkdir()
        socket = tmux_dir / "tmux.sock"
        session = f"macs-test-{os.getpid()}"
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", "worker"],
            check=True,
            capture_output=True,
            text=True,
        )

        fake_bin = self.temp_dir / "bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text("#!/usr/bin/env bash\nsleep 10\n", encoding="utf-8")
        fake_codex.chmod(0o755)

        env = self.env.copy()
        env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]

        launch_cmd = [
            str(START_CONTROLLER),
            "--repo",
            str(self.repo_root),
            "--skills",
            str(REPO_ROOT / ".codex" / "skills"),
            "--tmux-socket",
            str(socket),
            "--tmux-session",
            session,
            "--codex-args",
            "--sandbox danger-full-access",
        ]

        holder = subprocess.Popen(
            launch_cmd,
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            lock_path = self.repo_root / ".codex" / "orchestration" / "controller.lock"
            for _ in range(50):
                if lock_path.exists() and lock_path.read_text(encoding="utf-8").strip():
                    break
                time.sleep(0.1)
            else:
                self.fail("launcher did not acquire the controller lock")

            contender = subprocess.run(
                launch_cmd,
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(contender.returncode, 2, contender.stdout + contender.stderr)
            self.assertIn("Another controller session is already active", contender.stderr)
            self.assertIn(session, contender.stderr)
        finally:
            holder.send_signal(signal.SIGTERM)
            holder.wait(timeout=5)
            if holder.stdout is not None:
                holder.stdout.close()
            if holder.stderr is not None:
                holder.stderr.close()
            subprocess.run(
                ["tmux", "-S", str(socket), "kill-server"],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_eventful_transaction_commits_sqlite_and_ndjson(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        baseline_lines = events_ndjson.read_text(encoding="utf-8").splitlines()

        event = EventRecord(
            event_id="evt-001",
            event_type="worker.registered",
            aggregate_type="worker",
            aggregate_id="worker-codex-1",
            timestamp="2026-04-09T20:00:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-001",
            causation_id=None,
            payload={"runtime_type": "codex", "state": "registered"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-1",
                    "codex",
                    "codex",
                    "/tmp/test.sock",
                    "macs",
                    "%1",
                    "registered",
                    "[]",
                    "required_only",
                    None,
                    None,
                    "interruptible",
                    "[]",
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, event, mutator)

        conn = sqlite3.connect(state_db)
        try:
            worker = conn.execute(
                "SELECT worker_id, runtime_type, state FROM workers WHERE worker_id = ?",
                ("worker-codex-1",),
            ).fetchone()
            event_row = conn.execute(
                "SELECT event_id, event_type, aggregate_id FROM events WHERE event_id = ?",
                ("evt-001",),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(worker, ("worker-codex-1", "codex", "registered"))
        self.assertEqual(event_row, ("evt-001", "worker.registered", "worker-codex-1"))

        lines = events_ndjson.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), len(baseline_lines) + 1)
        exported = json.loads(lines[-1])
        self.assertEqual(exported["event_id"], "evt-001")
        self.assertEqual(exported["aggregate_id"], "worker-codex-1")

    def test_failed_transaction_does_not_append_ndjson(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        baseline_text = events_ndjson.read_text(encoding="utf-8")

        event = EventRecord(
            event_id="evt-rollback",
            event_type="worker.registered",
            aggregate_type="worker",
            aggregate_id="worker-fail",
            timestamp="2026-04-09T20:00:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-rollback",
            causation_id=None,
            payload={"runtime_type": "codex"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                "INSERT INTO workers (worker_id, runtime_type, state) VALUES (?, ?, ?)",
                ("worker-fail", "codex", "registered"),
            )
            raise RuntimeError("force rollback")

        with self.assertRaises(RuntimeError):
            write_eventful_transaction(state_db, events_ndjson, event, mutator)

        conn = sqlite3.connect(state_db)
        try:
            worker_count = conn.execute(
                "SELECT COUNT(*) FROM workers WHERE worker_id = ?",
                ("worker-fail",),
            ).fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_id = ?",
                ("evt-rollback",),
            ).fetchone()[0]
        finally:
            conn.close()

        self.assertEqual(worker_count, 0)
        self.assertEqual(event_count, 0)
        self.assertEqual(events_ndjson.read_text(encoding="utf-8"), baseline_text)

    def test_task_cannot_have_two_live_leases(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-001",
                title="Invariant test",
                description="Ensure one live lease",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=[],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id="evt-task-001",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-001",
                timestamp="2026-04-09T20:10:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-001",
                causation_id=None,
                payload={"task_id": "task-001"},
                redaction_level="none",
            ),
        )

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-001",
                task_id="task-001",
                worker_id="worker-001",
                state="active",
                issued_at="2026-04-09T20:11:00+01:00",
                accepted_at="2026-04-09T20:11:01+01:00",
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-001",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-001",
                timestamp="2026-04-09T20:11:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-001",
                causation_id=None,
                payload={"task_id": "task-001", "worker_id": "worker-001"},
                redaction_level="none",
            ),
        )

        with self.assertRaises(InvariantViolationError):
            issue_lease(
                state_db,
                events_ndjson,
                LeaseRecord(
                    lease_id="lease-002",
                    task_id="task-001",
                    worker_id="worker-002",
                    state="active",
                    issued_at="2026-04-09T20:12:00+01:00",
                    accepted_at=None,
                    ended_at=None,
                    replacement_lease_id=None,
                    intervention_reason=None,
                    evidence_version="v1",
                ),
                EventRecord(
                    event_id="evt-lease-002",
                    event_type="lease.issued",
                    aggregate_type="lease",
                    aggregate_id="lease-002",
                    timestamp="2026-04-09T20:12:00+01:00",
                    actor_type="controller",
                    actor_id="controller-main",
                    correlation_id="corr-lease-002",
                    causation_id=None,
                    payload={"task_id": "task-001", "worker_id": "worker-002"},
                    redaction_level="none",
                ),
            )

        conn = sqlite3.connect(state_db)
        try:
            live_count = conn.execute(
                "SELECT COUNT(*) FROM leases WHERE task_id = ? AND state IN ('active','paused','suspended','expiring')",
                ("task-001",),
            ).fetchone()[0]
            current_task = conn.execute(
                "SELECT current_worker_id, current_lease_id FROM tasks WHERE task_id = ?",
                ("task-001",),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(live_count, 1)
        self.assertEqual(current_task, ("worker-001", "lease-001"))

    def test_successor_lease_requires_predecessor_to_end(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-002",
                title="Replacement flow",
                description="Replacement flow",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=[],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id="evt-task-002",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-002",
                timestamp="2026-04-09T20:20:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-002",
                causation_id=None,
                payload={"task_id": "task-002"},
                redaction_level="none",
            ),
        )

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-101",
                task_id="task-002",
                worker_id="worker-101",
                state="active",
                issued_at="2026-04-09T20:21:00+01:00",
                accepted_at=None,
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-101",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-101",
                timestamp="2026-04-09T20:21:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-101",
                causation_id=None,
                payload={"task_id": "task-002"},
                redaction_level="none",
            ),
        )

        transition_lease_state(
            state_db,
            events_ndjson,
            "lease-101",
            "revoked",
            ended_at="2026-04-09T20:22:00+01:00",
            replacement_lease_id="lease-102",
            event=EventRecord(
                event_id="evt-lease-101-revoked",
                event_type="lease.revoked",
                aggregate_type="lease",
                aggregate_id="lease-101",
                timestamp="2026-04-09T20:22:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-101-revoked",
                causation_id=None,
                payload={"replacement_lease_id": "lease-102"},
                redaction_level="none",
            ),
        )

        transition_lease_state(
            state_db,
            events_ndjson,
            "lease-101",
            "replaced",
            ended_at="2026-04-09T20:22:01+01:00",
            replacement_lease_id="lease-102",
            event=EventRecord(
                event_id="evt-lease-101-replaced",
                event_type="lease.replaced",
                aggregate_type="lease",
                aggregate_id="lease-101",
                timestamp="2026-04-09T20:22:01+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-101-replaced",
                causation_id=None,
                payload={"replacement_lease_id": "lease-102"},
                redaction_level="none",
            ),
        )

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-102",
                task_id="task-002",
                worker_id="worker-102",
                state="active",
                issued_at="2026-04-09T20:23:00+01:00",
                accepted_at=None,
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-102",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-102",
                timestamp="2026-04-09T20:23:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-102",
                causation_id=None,
                payload={"task_id": "task-002"},
                redaction_level="none",
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            leases = conn.execute(
                "SELECT lease_id, state, replacement_lease_id FROM leases WHERE task_id = ? ORDER BY lease_id",
                ("task-002",),
            ).fetchall()
            task = conn.execute(
                "SELECT current_worker_id, current_lease_id FROM tasks WHERE task_id = ?",
                ("task-002",),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(
            leases,
            [
                ("lease-101", "replaced", "lease-102"),
                ("lease-102", "active", None),
            ],
        )
        self.assertEqual(task, ("worker-102", "lease-102"))

    def test_invalid_lease_transition_is_rejected(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-003",
                title="Invalid transition test",
                description="Invalid transition test",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=[],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id="evt-task-003",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-003",
                timestamp="2026-04-09T20:30:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-003",
                causation_id=None,
                payload={"task_id": "task-003"},
                redaction_level="none",
            ),
        )

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-201",
                task_id="task-003",
                worker_id="worker-201",
                state="active",
                issued_at="2026-04-09T20:31:00+01:00",
                accepted_at=None,
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-201",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-201",
                timestamp="2026-04-09T20:31:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-201",
                causation_id=None,
                payload={"task_id": "task-003"},
                redaction_level="none",
            ),
        )

        with self.assertRaises(InvariantViolationError):
            transition_lease_state(
                state_db,
                events_ndjson,
                "lease-201",
                "replaced",
                ended_at="2026-04-09T20:32:00+01:00",
                replacement_lease_id="lease-202",
                event=EventRecord(
                    event_id="evt-lease-201-invalid",
                    event_type="lease.replaced",
                    aggregate_type="lease",
                    aggregate_id="lease-201",
                    timestamp="2026-04-09T20:32:00+01:00",
                    actor_type="controller",
                    actor_id="controller-main",
                    correlation_id="corr-lease-201-invalid",
                    causation_id=None,
                    payload={"replacement_lease_id": "lease-202"},
                    redaction_level="none",
                ),
            )

    def test_task_cannot_complete_while_live_lease_exists(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-004",
                title="Task transition guard",
                description="Task transition guard",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=[],
                priority="normal",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id="evt-task-004",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-004",
                timestamp="2026-04-09T20:40:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-004",
                causation_id=None,
                payload={"task_id": "task-004"},
                redaction_level="none",
            ),
        )

        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-301",
                task_id="task-004",
                worker_id="worker-301",
                state="pending_accept",
                issued_at="2026-04-09T20:41:00+01:00",
                accepted_at=None,
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-301",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-301",
                timestamp="2026-04-09T20:41:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-301",
                causation_id=None,
                payload={"task_id": "task-004"},
                redaction_level="none",
            ),
        )

        transition_task_state(
            state_db,
            events_ndjson,
            "task-004",
            "reserved",
            EventRecord(
                event_id="evt-task-004-reserved",
                event_type="task.reserved",
                aggregate_type="task",
                aggregate_id="task-004",
                timestamp="2026-04-09T20:42:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-004-reserved",
                causation_id=None,
                payload={"task_id": "task-004"},
                redaction_level="none",
            ),
        )

        transition_lease_state(
            state_db,
            events_ndjson,
            "lease-301",
            "active",
            ended_at=None,
            replacement_lease_id=None,
            event=EventRecord(
                event_id="evt-lease-301-active",
                event_type="lease.activated",
                aggregate_type="lease",
                aggregate_id="lease-301",
                timestamp="2026-04-09T20:43:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-301-active",
                causation_id=None,
                payload={"task_id": "task-004"},
                redaction_level="none",
            ),
        )

        transition_task_state(
            state_db,
            events_ndjson,
            "task-004",
            "active",
            EventRecord(
                event_id="evt-task-004-active",
                event_type="task.activated",
                aggregate_type="task",
                aggregate_id="task-004",
                timestamp="2026-04-09T20:44:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-004-active",
                causation_id=None,
                payload={"task_id": "task-004"},
                redaction_level="none",
            ),
        )

        with self.assertRaises(InvariantViolationError):
            transition_task_state(
                state_db,
                events_ndjson,
                "task-004",
                "completed",
                EventRecord(
                    event_id="evt-task-004-completed",
                    event_type="task.completed",
                    aggregate_type="task",
                    aggregate_id="task-004",
                    timestamp="2026-04-09T20:45:00+01:00",
                    actor_type="controller",
                    actor_id="controller-main",
                    correlation_id="corr-task-004-completed",
                    causation_id=None,
                    payload={"task_id": "task-004"},
                    redaction_level="none",
                ),
            )

    def test_partial_unique_index_rejects_second_live_lease(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, workflow_class, intent,
                    required_capabilities, protected_surfaces, priority, state,
                    current_worker_id, current_lease_id, routing_policy_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "task-005",
                    "Schema guard",
                    "Schema guard",
                    "implementation",
                    "test",
                    "[]",
                    "[]",
                    "normal",
                    "pending_assignment",
                    None,
                    None,
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, task_id, worker_id, state, issued_at, accepted_at,
                    ended_at, replacement_lease_id, intervention_reason, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                ("lease-401", "task-005", "worker-401", "active", "t1", None, None, None, None, "v1"),
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    """
                    INSERT INTO leases (
                        lease_id, task_id, worker_id, state, issued_at, accepted_at,
                        ended_at, replacement_lease_id, intervention_reason, evidence_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("lease-402", "task-005", "worker-402", "paused", "t2", None, None, None, None, "v1"),
                )
        finally:
            conn.close()

    def test_restart_marks_live_ownership_for_reconciliation(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-006",
                title="Restart recovery",
                description="Restart recovery",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=["/repo/file.txt"],
                priority="high",
                state="pending_assignment",
                current_worker_id=None,
                current_lease_id=None,
                routing_policy_ref=None,
            ),
            EventRecord(
                event_id="evt-task-006",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-006",
                timestamp="2026-04-09T21:00:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-006",
                causation_id=None,
                payload={"task_id": "task-006"},
                redaction_level="none",
            ),
        )
        transition_task_state(
            state_db,
            events_ndjson,
            "task-006",
            "reserved",
            EventRecord(
                event_id="evt-task-006-reserved",
                event_type="task.reserved",
                aggregate_type="task",
                aggregate_id="task-006",
                timestamp="2026-04-09T21:00:10+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-006-reserved",
                causation_id=None,
                payload={"task_id": "task-006"},
                redaction_level="none",
            ),
        )
        issue_lease(
            state_db,
            events_ndjson,
            LeaseRecord(
                lease_id="lease-501",
                task_id="task-006",
                worker_id="worker-501",
                state="pending_accept",
                issued_at="2026-04-09T21:00:20+01:00",
                accepted_at=None,
                ended_at=None,
                replacement_lease_id=None,
                intervention_reason=None,
                evidence_version="v1",
            ),
            EventRecord(
                event_id="evt-lease-501",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-501",
                timestamp="2026-04-09T21:00:20+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-501",
                causation_id=None,
                payload={"task_id": "task-006"},
                redaction_level="none",
            ),
        )
        transition_lease_state(
            state_db,
            events_ndjson,
            "lease-501",
            "active",
            ended_at=None,
            replacement_lease_id=None,
            event=EventRecord(
                event_id="evt-lease-501-active",
                event_type="lease.activated",
                aggregate_type="lease",
                aggregate_id="lease-501",
                timestamp="2026-04-09T21:00:30+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-501-active",
                causation_id=None,
                payload={"task_id": "task-006"},
                redaction_level="none",
            ),
        )
        transition_task_state(
            state_db,
            events_ndjson,
            "task-006",
            "active",
            EventRecord(
                event_id="evt-task-006-active",
                event_type="task.activated",
                aggregate_type="task",
                aggregate_id="task-006",
                timestamp="2026-04-09T21:00:40+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-006-active",
                causation_id=None,
                payload={"task_id": "task-006"},
                redaction_level="none",
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                UPDATE tasks
                SET current_worker_id = ?, current_lease_id = ?
                WHERE task_id = ?
                """,
                ("worker-codex-pending", "lease-pending-accept", "task-pending-accept"),
            )
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id,
                    policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-501",
                    "path",
                    "/repo/file.txt",
                    "exclusive",
                    "held",
                    "task-006",
                    "lease-501",
                    "default",
                    "2026-04-09T21:00:45+01:00",
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["data"]["startup_summary"]

        self.assertTrue(summary["assignments_blocked"])
        self.assertEqual(summary["unresolved_anomalies"]["tasks_pending_reconciliation"], ["task-006"])
        self.assertEqual(summary["unresolved_anomalies"]["live_leases_pending_reconciliation"], ["lease-501"])
        self.assertEqual(summary["unresolved_anomalies"]["suspended_lease_ids"], ["lease-501"])
        self.assertEqual(summary["unresolved_anomalies"]["unreleased_lock_count"], 1)
        self.assertIsNotNone(summary["recovery_run_id"])

        conn = sqlite3.connect(state_db)
        try:
            task_row = conn.execute(
                "SELECT state, current_worker_id, current_lease_id FROM tasks WHERE task_id = ?",
                ("task-006",),
            ).fetchone()
            lease_row = conn.execute(
                "SELECT state FROM leases WHERE lease_id = ?",
                ("lease-501",),
            ).fetchone()
            metadata = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
            recovery_row = conn.execute(
                "SELECT state, anomaly_summary FROM recovery_runs WHERE recovery_run_id = ?",
                (summary["recovery_run_id"],),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(task_row, ("reconciliation", "worker-501", "lease-501"))
        self.assertEqual(lease_row, ("suspended",))
        self.assertEqual(metadata["assignments_blocked"], "1")
        self.assertIn("task-006", metadata["startup_summary"])
        self.assertEqual(recovery_row[0], "pending_reconciliation")
        self.assertIn("lease-501", recovery_row[1])

    def test_restart_summary_is_clean_when_no_live_ownership_exists(self) -> None:
        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["data"]["startup_summary"]

        self.assertFalse(summary["assignments_blocked"])
        self.assertEqual(summary["unresolved_anomalies"]["tasks_pending_reconciliation"], [])
        self.assertEqual(summary["unresolved_anomalies"]["live_leases_pending_reconciliation"], [])
        self.assertEqual(summary["unresolved_anomalies"]["suspended_lease_ids"], [])
        self.assertEqual(summary["unresolved_anomalies"]["unreleased_lock_count"], 0)
        self.assertIsNone(summary["recovery_run_id"])

    def test_assign_rejects_when_startup_recovery_blocks_assignments(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-hold-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-hold",
            timestamp="2026-04-09T21:05:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-hold-001",
            causation_id=None,
            payload={"worker_id": "worker-codex-hold"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-hold",
                    "codex",
                    "codex",
                    "/tmp/hold.sock",
                    "hold",
                    "%1",
                    "ready",
                    '["implementation"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Blocked until startup recovery clears",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "backend/recovery_gate.py",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO metadata(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                ("assignments_blocked", "1"),
            )
            conn.commit()
        finally:
            conn.close()

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 1)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(
            payload["error"]["message"],
            "Assignments are blocked pending startup recovery reconciliation",
        )

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["data"]["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["data"]["task"]["current_lease_id"])

    def test_restart_summary_flags_pending_accept_leases_for_reconciliation(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id="task-pending-accept",
                title="Recover half-assigned task",
                description="Recover half-assigned task",
                workflow_class="implementation",
                intent="test",
                required_capabilities=[],
                protected_surfaces=["backend/half_assigned.py"],
                priority="normal",
                state="reserved",
                current_worker_id="worker-codex-pending",
                current_lease_id="lease-pending-accept",
                routing_policy_ref="phase1-defaults-v1",
            ),
            EventRecord(
                event_id="evt-task-pending-accept",
                event_type="task.created",
                aggregate_type="task",
                aggregate_id="task-pending-accept",
                timestamp="2026-04-09T21:07:00+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-pending-accept",
                causation_id=None,
                payload={"task_id": "task-pending-accept"},
                redaction_level="none",
            ),
        )
        write_eventful_transaction(
            state_db,
            events_ndjson,
            EventRecord(
                event_id="evt-lease-pending-accept",
                event_type="lease.issued",
                aggregate_type="lease",
                aggregate_id="lease-pending-accept",
                timestamp="2026-04-09T21:07:10+01:00",
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-pending-accept",
                causation_id=None,
                payload={"task_id": "task-pending-accept"},
                redaction_level="none",
            ),
            lambda conn: (
                conn.execute(
                    """
                    INSERT INTO leases (
                        lease_id, task_id, worker_id, state, issued_at, accepted_at,
                        ended_at, replacement_lease_id, intervention_reason, evidence_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "lease-pending-accept",
                        "task-pending-accept",
                        "worker-codex-pending",
                        "pending_accept",
                        "2026-04-09T21:07:10+01:00",
                        None,
                        None,
                        None,
                        None,
                        "route-pending",
                    ),
                ),
                conn.execute(
                    """
                    UPDATE tasks
                    SET current_worker_id = ?, current_lease_id = ?
                    WHERE task_id = ?
                    """,
                    ("worker-codex-pending", "lease-pending-accept", "task-pending-accept"),
                ),
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id,
                    policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-pending-accept",
                    "path",
                    "backend/half_assigned.py",
                    "exclusive",
                    "held",
                    "task-pending-accept",
                    "lease-pending-accept",
                    "phase1-defaults-v1",
                    "2026-04-09T21:07:11+01:00",
                    None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["data"]["startup_summary"]

        self.assertTrue(summary["assignments_blocked"])
        self.assertEqual(summary["unresolved_anomalies"]["tasks_pending_reconciliation"], ["task-pending-accept"])
        self.assertEqual(summary["unresolved_anomalies"]["live_leases_pending_reconciliation"], ["lease-pending-accept"])
        self.assertEqual(summary["unresolved_anomalies"]["suspended_lease_ids"], [])
        self.assertEqual(summary["unresolved_anomalies"]["unreleased_lock_count"], 1)

        conn = sqlite3.connect(state_db)
        try:
            task_row = conn.execute(
                "SELECT state, current_worker_id, current_lease_id FROM tasks WHERE task_id = ?",
                ("task-pending-accept",),
            ).fetchone()
            lease_row = conn.execute(
                "SELECT state FROM leases WHERE lease_id = ?",
                ("lease-pending-accept",),
            ).fetchone()
            metadata = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
        finally:
            conn.close()

        self.assertEqual(task_row, ("reconciliation", "worker-codex-pending", "lease-pending-accept"))
        self.assertEqual(lease_row, ("pending_accept",))
        self.assertEqual(metadata["assignments_blocked"], "1")

    def test_worker_discover_records_tmux_backed_workers(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        tmux_dir = self.temp_dir / "tmux-workers"
        tmux_dir.mkdir()
        socket = tmux_dir / "workers.sock"
        session = f"macs-workers-{os.getpid()}"
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", "codex-main"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["tmux", "-S", str(socket), "new-window", "-t", session, "-n", "claude-review"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["tmux", "-S", str(socket), "select-pane", "-t", f"{session}:codex-main.0", "-T", "codex"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["tmux", "-S", str(socket), "select-pane", "-t", f"{session}:claude-review.0", "-T", "claude"],
            check=True,
            capture_output=True,
            text=True,
        )

        codex_dir = self.repo_root / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "tmux-socket.txt").write_text(f"{socket}\n", encoding="utf-8")
        (codex_dir / "tmux-session.txt").write_text(f"{session}\n", encoding="utf-8")

        try:
            result = self.run_cli("worker", "discover", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            workers = payload["data"]["workers"]

            self.assertEqual(payload["command"], "macs worker discover")
            self.assertEqual(payload["data"]["discovered_count"], 2)
            self.assertEqual(len(workers), 2)
            self.assertEqual([worker["runtime_type"] for worker in workers], ["claude", "codex"])
            self.assertTrue(all(worker["tmux_session"] == session for worker in workers))
            self.assertTrue(all(worker["tmux_socket"] == str(socket) for worker in workers))

            list_result = self.run_cli("worker", "list", "--json")
            self.assertEqual(list_result.returncode, 0, list_result.stderr)
            list_payload = json.loads(list_result.stdout)
            self.assertEqual(len(list_payload["data"]["workers"]), 2)
        finally:
            subprocess.run(
                ["tmux", "-S", str(socket), "kill-server"],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_worker_register_disable_enable_and_inspect(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        event = EventRecord(
            event_id="evt-worker-seed-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-local-seeded",
            timestamp="2026-04-09T21:40:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-001",
            causation_id=None,
            payload={"worker_id": "worker-local-seeded"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-local-seeded",
                    "local",
                    "local",
                    "/tmp/seed.sock",
                    "seed",
                    "%1",
                    "ready",
                    '["privacy_sensitive"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["discovered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, event, mutator)

        register_result = self.run_cli(
            "worker",
            "register",
            "--worker",
            "worker-local-seeded",
            "--adapter",
            "local",
            "--json",
        )
        self.assertEqual(register_result.returncode, 0, register_result.stderr)

        disable_result = self.run_cli("worker", "disable", "--worker", "worker-local-seeded", "--json")
        self.assertEqual(disable_result.returncode, 0, disable_result.stderr)
        disable_payload = json.loads(disable_result.stdout)
        self.assertEqual(disable_payload["data"]["worker"]["state"], "unavailable")
        self.assertIn("manual_disabled", disable_payload["data"]["worker"]["operator_tags"])

        enable_result = self.run_cli("worker", "enable", "--worker", "worker-local-seeded", "--json")
        self.assertEqual(enable_result.returncode, 0, enable_result.stderr)
        enable_payload = json.loads(enable_result.stdout)
        self.assertEqual(enable_payload["data"]["worker"]["state"], "ready")
        self.assertNotIn("manual_disabled", enable_payload["data"]["worker"]["operator_tags"])

        inspect_result = self.run_cli("worker", "inspect", "--worker", "worker-local-seeded", "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        self.assertEqual(inspect_payload["data"]["worker"]["adapter_id"], "local")
        self.assertEqual(inspect_payload["data"]["worker"]["state"], "ready")

    def test_manual_disable_survives_health_reclassification_reads(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        event = EventRecord(
            event_id="evt-worker-seed-manual-disable-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-local-disabled",
            timestamp="2026-04-09T21:42:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-manual-disable-001",
            causation_id=None,
            payload={"worker_id": "worker-local-disabled"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-local-disabled",
                    "local",
                    "local",
                    "/tmp/manual-disable.sock",
                    "manual-disable",
                    "%2",
                    "unavailable",
                    '["privacy_sensitive"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered","manual_disabled"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, event, mutator)

        inspect_result = self.run_cli("worker", "inspect", "--worker", "worker-local-disabled", "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        self.assertEqual(inspect_payload["data"]["worker"]["state"], "unavailable")
        self.assertIn("manual_disabled", inspect_payload["data"]["worker"]["operator_tags"])

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stderr)

        list_payload = json.loads(self.run_cli("worker", "list", "--json").stdout)
        worker = next(item for item in list_payload["data"]["workers"] if item["worker_id"] == "worker-local-disabled")
        self.assertEqual(worker["state"], "unavailable")
        self.assertIn("manual_disabled", worker["operator_tags"])

    def test_adapter_list_inspect_and_validate(self) -> None:
        list_result = self.run_cli("adapter", "list", "--json")
        self.assertEqual(list_result.returncode, 0, list_result.stderr)
        list_payload = json.loads(list_result.stdout)
        adapter_ids = [adapter["adapter_id"] for adapter in list_payload["data"]["adapters"]]
        self.assertEqual(adapter_ids, ["codex", "claude", "gemini", "local"])

        inspect_result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        self.assertEqual(inspect_payload["data"]["adapter"]["runtime_type"], "codex")
        self.assertIn("discover_workers", inspect_payload["data"]["adapter"]["supported_operations"])

        validate_result = self.run_cli("adapter", "validate", "--adapter", "codex", "--json")
        self.assertEqual(validate_result.returncode, 0, validate_result.stderr)
        validate_payload = json.loads(validate_result.stdout)
        self.assertTrue(validate_payload["data"]["validation"]["ok"])
        self.assertIn("token_budget", validate_payload["data"]["validation"]["unsupported_features"])

    def test_adapter_probe_returns_normalized_evidence(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        event = EventRecord(
            event_id="evt-worker-seed-002",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-seeded",
            timestamp="2026-04-09T21:45:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-002",
            causation_id=None,
            payload={"worker_id": "worker-codex-seeded"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-local-probe",
                    "local",
                    "local",
                    "/tmp/seed.sock",
                    "seed",
                    "%2",
                    "ready",
                    '["privacy_sensitive","documentation"]',
                    "required_only",
                    "2026-04-09T20:45:00+00:00",
                    "2026-04-09T20:45:00+00:00",
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, event, mutator)

        probe_result = self.run_cli("adapter", "probe", "--worker", "worker-local-probe", "--json")
        self.assertEqual(probe_result.returncode, 0, probe_result.stderr)
        probe_payload = json.loads(probe_result.stdout)
        worker = probe_payload["data"]["worker"]
        evidence = probe_payload["data"]["evidence"]

        self.assertEqual(worker["runtime"], "local")
        self.assertGreaterEqual(worker["freshness_seconds"], 0)
        self.assertEqual([item["adapter_id"] for item in evidence], ["local", "local", "local"])
        self.assertEqual(
            [item["name"] for item in evidence],
            ["pane_presence", "capability_decl", "health_state"],
        )
        self.assertTrue(all("freshness_seconds" in item for item in evidence))
        self.assertTrue(all("source_ref" in item for item in evidence))

    def test_codex_adapter_probe_surfaces_permission_signals(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.run_cli("setup", "init")
        tmux_dir = self.temp_dir / "tmux-codex-probe"
        tmux_dir.mkdir()
        socket = tmux_dir / "codex.sock"
        session = f"macs-codex-{os.getpid()}"
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", "codex-worker"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["tmux", "-S", str(socket), "select-pane", "-t", f"{session}:codex-worker.0", "-T", "codex"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "tmux",
                "-S",
                str(socket),
                "send-keys",
                "-t",
                f"{session}:codex-worker.0",
                '-l',
                'CODEX_HOME="/tmp/repo/.codex" codex --yolo --sandbox danger-full-access --model gpt-5.4',
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        codex_dir = self.repo_root / ".codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        (codex_dir / "tmux-socket.txt").write_text(f"{socket}\n", encoding="utf-8")
        (codex_dir / "tmux-session.txt").write_text(f"{session}\n", encoding="utf-8")

        try:
            discover_result = self.run_cli("worker", "discover", "--json")
            self.assertEqual(discover_result.returncode, 0, discover_result.stderr)
            discover_payload = json.loads(discover_result.stdout)
            worker_id = discover_payload["data"]["workers"][0]["worker_id"]

            probe_result = self.run_cli("adapter", "probe", "--worker", worker_id, "--json")
            self.assertEqual(probe_result.returncode, 0, probe_result.stderr)
            probe_payload = json.loads(probe_result.stdout)
            evidence = probe_payload["data"]["evidence"]
            permission_surface = evidence[-1]

            self.assertEqual(permission_surface["name"], "permission_surface")
            self.assertEqual(permission_surface["value"]["approval_policy"], "yolo")
            self.assertEqual(permission_surface["value"]["sandbox"], "danger-full-access")
            self.assertEqual(permission_surface["value"]["model"], "gpt-5.4")
            self.assertEqual(permission_surface["confidence"], "medium")
        finally:
            subprocess.run(
                ["tmux", "-S", str(socket), "kill-server"],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_codex_adapter_probe_does_not_consume_adjacent_text_after_model_flag(self) -> None:
        adapter = CodexAdapter()
        worker = {
            "worker_id": "worker-codex-regex",
            "tmux_socket": "/tmp/codex-regex.sock",
            "tmux_session": "regex",
            "tmux_pane": "%3",
            "state": "ready",
            "capabilities": ["implementation"],
            "required_signal_status": "required_only",
            "interruptibility": "interruptible",
            "freshness_seconds": 5,
        }

        with mock.patch.object(
            adapter,
            "capture",
            return_value={"ok": True, "adapter_id": "codex", "worker_id": "worker-codex-regex", "output": "codex --model gpt-5.4\nWelcome\n"},
        ):
            permission_surface = adapter.probe(worker)[-1]

        self.assertEqual(permission_surface["value"]["model"], "gpt-5.4")

    def test_claude_gemini_and_local_adapters_degrade_safely(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        event = EventRecord(
            event_id="evt-worker-seed-003",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-claude-seeded",
            timestamp="2026-04-09T21:50:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-003",
            causation_id=None,
            payload={"worker_ids": ["worker-claude-seeded", "worker-gemini-seeded", "worker-local-seeded-2"]},
            redaction_level="none",
        )

        def mutator(conn):
            rows = [
                (
                    "worker-claude-seeded",
                    "claude",
                    "claude",
                    "/tmp/seed.sock",
                    "seed",
                    "%3",
                    "ready",
                    '["analysis","review"]',
                    "required_only",
                ),
                (
                    "worker-gemini-seeded",
                    "gemini",
                    "gemini",
                    "/tmp/seed.sock",
                    "seed",
                    "%4",
                    "ready",
                    '["planning","solutioning"]',
                    "required_only",
                ),
                (
                    "worker-local-seeded-2",
                    "local",
                    "local",
                    "/tmp/seed.sock",
                    "seed",
                    "%5",
                    "ready",
                    '["privacy_sensitive","documentation"]',
                    "required_only",
                ),
            ]
            for worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane, state, capabilities, required_signal_status in rows:
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
                        capabilities,
                        required_signal_status,
                        "2026-04-09T20:50:00+00:00",
                        "2026-04-09T20:50:00+00:00",
                        "interruptible",
                        '["registered"]',
                    ),
                )

        write_eventful_transaction(state_db, events_ndjson, event, mutator)

        for worker_id, adapter_id in (
            ("worker-claude-seeded", "claude"),
            ("worker-gemini-seeded", "gemini"),
            ("worker-local-seeded-2", "local"),
        ):
            validate_result = self.run_cli("adapter", "validate", "--adapter", adapter_id, "--json")
            self.assertEqual(validate_result.returncode, 0, validate_result.stderr)
            validate_payload = json.loads(validate_result.stdout)
            self.assertTrue(validate_payload["data"]["validation"]["ok"])
            self.assertGreaterEqual(len(validate_payload["data"]["validation"]["unsupported_features"]), 2)

            probe_result = self.run_cli("adapter", "probe", "--worker", worker_id, "--json")
            self.assertEqual(probe_result.returncode, 0, probe_result.stderr)
            probe_payload = json.loads(probe_result.stdout)
            self.assertEqual(probe_payload["data"]["worker"]["adapter_id"], adapter_id)
            self.assertEqual(
                [item["name"] for item in probe_payload["data"]["evidence"]],
                ["pane_presence", "capability_decl", "health_state"],
            )

    def test_task_assign_records_routing_decision_and_locks(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-route-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-route",
            timestamp="2026-04-09T22:20:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-route-001",
            causation_id=None,
            payload={"worker_ids": ["worker-codex-route", "worker-local-route"]},
            redaction_level="none",
        )

        def mutator(conn):
            rows = [
                (
                    "worker-codex-route",
                    "codex",
                    "codex",
                    "ready",
                    '["implementation","review"]',
                    "interruptible",
                ),
                (
                    "worker-local-route",
                    "local",
                    "local",
                    "ready",
                    '["privacy_sensitive_offline"]',
                    "interruptible",
                ),
            ]
            for worker_id, runtime_type, adapter_id, state, capabilities, interruptibility in rows:
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
                        "/tmp/route.sock",
                        "route",
                        "%1",
                        state,
                        capabilities,
                        "required_only",
                        self.iso_now(seconds_ago=5),
                        self.iso_now(seconds_ago=5),
                        interruptibility,
                        '["registered"]',
                    ),
                )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        create_result = self.run_cli(
            "task",
            "create",
            "--summary",
            "Implement lock-safe routing",
            "--workflow-class",
            "implementation",
            "--require-capability",
            "implementation",
            "--surface",
            "backend/api/server.py",
            "--json",
        )
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        create_payload = json.loads(create_result.stdout)
        task_id = create_payload["data"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        result = assign_payload["data"]["result"]

        self.assertEqual(result["selected_worker_id"], "worker-codex-route")
        self.assertEqual(result["task"]["state"], "reserved")
        self.assertEqual(result["task"]["current_worker_id"], "worker-codex-route")
        self.assertIsNotNone(result["task"]["routing_decision"])
        self.assertEqual(result["task"]["routing_decision"]["selected_worker_id"], "worker-codex-route")
        self.assertEqual(len(result["locks"]), 1)
        self.assertEqual(result["locks"][0]["surface_ref"], "backend/api/server.py")

        inspect_result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        inspected_task = inspect_payload["data"]["task"]
        self.assertEqual(inspected_task["current_lease_id"], result["lease_id"])
        self.assertEqual(inspected_task["routing_policy_ref"], "phase1-defaults-v1")
        self.assertEqual(inspected_task["routing_decision"]["rationale"]["policy_version"], "phase1-defaults-v1")

        lock_result = self.run_cli("lock", "list", "--json")
        self.assertEqual(lock_result.returncode, 0, lock_result.stderr)
        lock_payload = json.loads(lock_result.stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["task_id"], task_id)

    def test_task_assign_rejects_conflicting_surface_lock(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-route-002",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-conflict",
            timestamp="2026-04-09T22:25:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-route-002",
            causation_id=None,
            payload={"worker_id": "worker-codex-conflict"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-conflict",
                    "codex",
                    "codex",
                    "/tmp/route.sock",
                    "route",
                    "%2",
                    "ready",
                    '["implementation"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        first_task = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "First task",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "docs/architecture/",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]
        first_assign = self.run_cli("task", "assign", "--task", first_task, "--json")
        self.assertEqual(first_assign.returncode, 0, first_assign.stderr)

        second_task = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Second task",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "docs/architecture/decision.md",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]

        second_assign = self.run_cli("task", "assign", "--task", second_task, "--json")
        self.assertEqual(second_assign.returncode, 1)
        self.assertIn("conflicting_lock_id", second_assign.stdout + second_assign.stderr)

    def test_task_assign_rejects_stale_workers_without_prior_health_refresh(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-stale-routing-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-stale",
            timestamp="2026-04-09T22:27:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-stale-routing-001",
            causation_id=None,
            payload={"worker_id": "worker-codex-stale"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-stale",
                    "codex",
                    "codex",
                    "/tmp/stale.sock",
                    "stale",
                    "%4",
                    "ready",
                    '["implementation"]',
                    "required_only",
                    self.iso_now(seconds_ago=120),
                    self.iso_now(seconds_ago=120),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Reject stale route target",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "backend/stale_routing.py",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 1)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(payload["error"]["message"], "No eligible workers for task")

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["data"]["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["data"]["task"]["current_worker_id"])

    def test_privacy_sensitive_routing_prefers_local_only(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-route-003",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-local-privacy",
            timestamp="2026-04-09T22:30:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-route-003",
            causation_id=None,
            payload={"worker_ids": ["worker-local-privacy", "worker-codex-privacy"]},
            redaction_level="none",
        )

        def mutator(conn):
            rows = [
                ("worker-local-privacy", "local", "local", '["privacy_sensitive_offline"]'),
                ("worker-codex-privacy", "codex", "codex", '["privacy_sensitive_offline"]'),
            ]
            for worker_id, runtime_type, adapter_id, capabilities in rows:
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
                        "/tmp/privacy.sock",
                        "privacy",
                        "%3",
                        "ready",
                        capabilities,
                        "required_only",
                        self.iso_now(seconds_ago=5),
                        self.iso_now(seconds_ago=5),
                        "interruptible",
                        '["registered"]',
                    ),
                )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Handle private material",
                "--workflow-class",
                "privacy_sensitive_offline",
                "--require-capability",
                "privacy_sensitive_offline",
                "--surface",
                "logical:privacy",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertEqual(assign_payload["data"]["result"]["selected_worker_id"], "worker-local-privacy")

    def test_task_assign_reports_unknown_workflow_class_without_traceback(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-unknown-workflow-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-unknown-workflow",
            timestamp="2026-04-09T22:31:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-unknown-workflow-001",
            causation_id=None,
            payload={"worker_id": "worker-codex-unknown-workflow"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-unknown-workflow",
                    "codex",
                    "codex",
                    "/tmp/unknown-workflow.sock",
                    "unknown-workflow",
                    "%5",
                    "ready",
                    '["implementation"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Unknown workflow class",
                "--workflow-class",
                "implementaiton",
                "--require-capability",
                "implementation",
                "--surface",
                "backend/typo.py",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 1)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(payload["error"]["message"], "Unsupported workflow class: implementaiton")
        self.assertNotIn("Traceback", assign_result.stderr)

    def test_lease_and_event_inspection_surface_assignment_history(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-route-004",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-history",
            timestamp="2026-04-09T22:35:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-route-004",
            causation_id=None,
            payload={"worker_id": "worker-codex-history"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-codex-history",
                    "codex",
                    "codex",
                    "/tmp/history.sock",
                    "history",
                    "%6",
                    "ready",
                    '["implementation"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "History task",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "frontend/app.js",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]
        assign_payload = json.loads(self.run_cli("task", "assign", "--task", task_id, "--json").stdout)
        lease_id = assign_payload["data"]["result"]["lease_id"]

        lease_inspect = self.run_cli("lease", "inspect", "--lease", lease_id, "--json")
        self.assertEqual(lease_inspect.returncode, 0, lease_inspect.stderr)
        lease_payload = json.loads(lease_inspect.stdout)
        self.assertEqual(lease_payload["data"]["lease"]["task_id"], task_id)
        self.assertEqual(lease_payload["data"]["lease"]["state"], "pending_accept")

        lease_history = self.run_cli("lease", "history", "--task", task_id, "--json")
        self.assertEqual(lease_history.returncode, 0, lease_history.stderr)
        history_payload = json.loads(lease_history.stdout)
        self.assertEqual(len(history_payload["data"]["leases"]), 1)
        self.assertEqual(history_payload["data"]["leases"][0]["lease_id"], lease_id)

        event_list = self.run_cli("event", "list", "--json")
        self.assertEqual(event_list.returncode, 0, event_list.stderr)
        event_list_payload = json.loads(event_list.stdout)
        event_ids = [item["event_id"] for item in event_list_payload["data"]["events"]]
        self.assertGreaterEqual(len(event_ids), 4)

        event_inspect = self.run_cli("event", "inspect", "--event", event_ids[-1], "--json")
        self.assertEqual(event_inspect.returncode, 0, event_inspect.stderr)
        event_inspect_payload = json.loads(event_inspect.stdout)
        self.assertIn("payload", event_inspect_payload["data"]["event"])

    def test_overview_show_summarizes_controller_state(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-overview-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-overview",
            timestamp="2026-04-09T22:40:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-overview-001",
            causation_id=None,
            payload={"worker_ids": ["worker-codex-overview", "worker-claude-overview"]},
            redaction_level="none",
        )

        def mutator(conn):
            rows = [
                ("worker-codex-overview", "codex", "ready", '["implementation"]'),
                ("worker-claude-overview", "claude", "degraded", '["planning_docs"]'),
            ]
            for worker_id, runtime_type, state, capabilities in rows:
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
                        "/tmp/overview.sock",
                        "overview",
                        "%7",
                        state,
                        capabilities,
                        "required_only",
                        self.iso_now(seconds_ago=5 if state == "ready" else 120),
                        self.iso_now(seconds_ago=5 if state == "ready" else 120),
                        "interruptible",
                        '["registered"]',
                    ),
                )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Overview task",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "src/main.ts",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        overview = overview_payload["data"]["overview"]

        self.assertEqual(overview["worker_summary"]["ready"], 1)
        self.assertEqual(overview["worker_summary"]["degraded"], 1)
        self.assertEqual(overview["task_summary"]["reserved"], 1)
        self.assertEqual(overview["locks"]["held_or_reserved"], 1)
        self.assertEqual(len(overview["active_alerts"]), 1)
        self.assertEqual(overview["active_tasks"][0]["task_id"], task_id)

    def test_overview_reclassifies_stale_workers(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-health-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-claude-stale",
            timestamp="2026-04-09T22:50:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-health-001",
            causation_id=None,
            payload={"worker_id": "worker-claude-stale"},
            redaction_level="none",
        )

        def mutator(conn):
            conn.execute(
                """
                INSERT INTO workers (
                    worker_id, runtime_type, adapter_id, tmux_socket, tmux_session, tmux_pane,
                    state, capabilities, required_signal_status, last_evidence_at,
                    last_heartbeat_at, interruptibility, operator_tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "worker-claude-stale",
                    "claude",
                    "claude",
                    "/tmp/stale.sock",
                    "stale",
                    "%8",
                    "ready",
                    '["planning_docs"]',
                    "required_only",
                    self.iso_now(seconds_ago=120),
                    self.iso_now(seconds_ago=120),
                    "interruptible",
                    '["registered"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        self.assertEqual(overview_payload["data"]["overview"]["worker_summary"]["degraded"], 1)
        self.assertEqual(overview_payload["data"]["health_changes"][0]["next_state"], "degraded")

    def test_routing_excludes_degraded_workers(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-health-002",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-stale",
            timestamp="2026-04-09T22:55:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-health-002",
            causation_id=None,
            payload={"worker_ids": ["worker-codex-stale", "worker-local-fresh"]},
            redaction_level="none",
        )

        def mutator(conn):
            rows = [
                (
                    "worker-codex-stale",
                    "codex",
                    "codex",
                    self.iso_now(seconds_ago=120),
                    '["implementation"]',
                ),
                (
                    "worker-local-fresh",
                    "local",
                    "local",
                    self.iso_now(seconds_ago=5),
                    '["implementation"]',
                ),
            ]
            for worker_id, runtime_type, adapter_id, last_evidence_at, capabilities in rows:
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
                        "/tmp/health-route.sock",
                        "health",
                        "%9",
                        "ready",
                        capabilities,
                        "required_only",
                        last_evidence_at,
                        last_evidence_at,
                        "interruptible",
                        '["registered"]',
                    ),
                )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)
        self.run_cli("overview", "show", "--json")

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Fresh routing only",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "pkg/service.py",
                "--json",
            ).stdout
        )["data"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertEqual(assign_payload["data"]["result"]["selected_worker_id"], "worker-local-fresh")


if __name__ == "__main__":
    unittest.main()
