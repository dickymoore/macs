#!/usr/bin/env python3
"""Black-box CLI contract tests for task lifecycle actions."""

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

from tools.orchestration.checkpoints import current_repo_fingerprint
from tools.orchestration.invariants import LeaseRecord, TaskRecord, create_task, issue_lease, transition_task_state
from tools.orchestration.store import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = [sys.executable, "-m", "tools.orchestration.cli.main"]


class TaskLifecycleCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-task-cli-test-"))
        self.repo_root = self.temp_dir / "repo"
        self.repo_root.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + self.env.get("PYTHONPATH", "")
        self.env["TMUX_SESSION"] = "macs-test"
        self.env["TMUX_SOCKET"] = "/tmp/macs-test.sock"

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

    def run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=self.repo_root,
                env=self.env,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            self.skipTest("git not available")

    def init_git_repo(self) -> None:
        init_result = self.run_git("init")
        self.assertEqual(init_result.returncode, 0, init_result.stdout + init_result.stderr)
        self.assertEqual(self.run_git("config", "user.email", "checkpoint@example.test").returncode, 0)
        self.assertEqual(self.run_git("config", "user.name", "Checkpoint Test").returncode, 0)
        (self.repo_root / ".gitignore").write_text(".codex/\n", encoding="utf-8")
        (self.repo_root / "README.md").write_text("baseline\n", encoding="utf-8")
        add_result = self.run_git("add", ".gitignore", "README.md")
        self.assertEqual(add_result.returncode, 0, add_result.stdout + add_result.stderr)
        commit_result = self.run_git("commit", "-m", "Initial commit")
        self.assertEqual(commit_result.returncode, 0, commit_result.stdout + commit_result.stderr)

    def create_checkpointable_repo_changes(self) -> None:
        readme_path = self.repo_root / "README.md"
        readme_path.write_text(readme_path.read_text(encoding="utf-8") + "checkpoint change\n", encoding="utf-8")
        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "checkpoint-notes.md").write_text("checkpoint notes\n", encoding="utf-8")

    def create_untracked_only_repo_changes(self) -> None:
        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "untracked-only-checkpoint.md").write_text(
            "untracked only checkpoint evidence\n",
            encoding="utf-8",
        )

    def capture_task_checkpoint(
        self,
        task_id: str,
        target_action: str,
        *,
        operator_id: str = "operator.checkpoint@example.test",
    ) -> dict[str, object]:
        result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            target_action,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": operator_id},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def insert_review_checkpoint(
        self,
        *,
        checkpoint_id: str,
        task_id: str,
        target_action: str,
        captured_at: str,
        affected_refs: dict[str, object],
        baseline_fingerprint: dict[str, object],
        actor_id: str = "operator.checkpoint@example.test",
    ) -> None:
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO review_checkpoints (
                    checkpoint_id, task_id, target_action, actor_type, actor_id, captured_at,
                    event_id, decision_event_id, affected_refs, evidence_refs, baseline_fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    task_id,
                    target_action,
                    "operator",
                    actor_id,
                    captured_at,
                    f"evt-review-checkpoint-seed-{checkpoint_id.split('-')[-1]}",
                    None,
                    json.dumps(affected_refs, sort_keys=True),
                    json.dumps({"bundle_dir": f".codex/orchestration/checkpoints/{checkpoint_id}"}, sort_keys=True),
                    json.dumps(baseline_fingerprint, sort_keys=True),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def seed_worker(self, worker_id: str = "worker-codex-contract") -> str:
        return self.seed_worker_with_tmux(
            worker_id=worker_id,
            tmux_socket=self.env["TMUX_SOCKET"],
            tmux_session=self.env["TMUX_SESSION"],
            tmux_pane="%1",
        )

    def seed_worker_with_tmux(
        self,
        *,
        worker_id: str = "worker-codex-contract",
        tmux_socket: str,
        tmux_session: str,
        tmux_pane: str,
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
                    "codex",
                    "codex",
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
                    "ready",
                    json.dumps(["implementation", "review", "solutioning"]),
                    "required_only",
                    self.iso_now(),
                    self.iso_now(),
                    "interruptible",
                    "[]",
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id

    def seed_worker_row(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        adapter_id: str,
        capabilities: list[str],
        operator_tags: list[str] | None = None,
        state: str = "ready",
        tmux_socket: str | None = None,
        tmux_session: str | None = None,
        tmux_pane: str = "%1",
        freshness_seconds: int = 0,
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
                    tmux_socket or self.env["TMUX_SOCKET"],
                    tmux_session or self.env["TMUX_SESSION"],
                    tmux_pane,
                    state,
                    json.dumps(capabilities),
                    "required_only",
                    self.iso_now(seconds_ago=freshness_seconds),
                    self.iso_now(seconds_ago=freshness_seconds),
                    "interruptible",
                    json.dumps(operator_tags or ["registered"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id

    def update_governance_policy(self, mutator) -> dict[str, object]:
        policy_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        updated = mutator(policy)
        policy_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return updated

    def update_adapter_settings(self, mutator) -> dict[str, object]:
        settings_path = self.repo_root / ".codex" / "orchestration" / "adapter-settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        updated = mutator(settings)
        settings_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return updated

    def configure_secret_scopes(
        self,
        scopes: list[dict[str, object]],
        *,
        allowlisted_surfaces: list[str] | None = None,
    ) -> dict[str, object]:
        surfaces = allowlisted_surfaces or sorted(
            {
                str(scope["surface_id"])
                for scope in scopes
                if isinstance(scope, dict) and scope.get("surface_id")
            }
        )
        return self.update_governance_policy(
            lambda policy: {
                **policy,
                "governed_surfaces": {
                    **policy["governed_surfaces"],
                    "allowlisted_surfaces": sorted(
                        set(policy["governed_surfaces"].get("allowlisted_surfaces", [])) | set(surfaces)
                    ),
                },
                "secret_scopes": scopes,
            }
        )

    def write_worker_env(self, values: dict[str, str]) -> Path:
        env_path = self.repo_root / ".codex" / "tmux-worker.env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{key}={json.dumps(value)}" for key, value in sorted(values.items())]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return env_path

    def seed_task(
        self,
        *,
        task_id: str = "task-contract-assign",
        summary: str = "Contract assign slice",
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
                timestamp=self.iso_now(),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-task-seed-{task_id}",
                causation_id=None,
                payload={"summary": summary, "workflow_class": workflow_class},
                redaction_level="none",
            ),
        )
        return task_id

    def seed_completed_task(self, *, task_id: str = "task-contract-archive") -> str:
        self.seed_task(task_id=task_id, summary="Archive contract slice")
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute("UPDATE tasks SET state = 'completed' WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()
        return task_id

    def start_tmux_worker(self) -> tuple[str, str, str]:
        tmux_dir = self.temp_dir / "tmux"
        tmux_dir.mkdir(exist_ok=True)
        socket = tmux_dir / "worker.sock"
        session = f"macs-task-{os.getpid()}"
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

    def configure_surface_version_pin(
        self,
        *,
        surface_id: str = "mcp",
        adapter_id: str,
        workflow_class: str = "implementation",
        expected_runtime_identity: str | None = None,
        expected_model_identity: str | None = None,
    ) -> dict[str, object]:
        pin = {
            "surface_id": surface_id,
            "adapter_id": adapter_id,
            "workflow_class": workflow_class,
            "operating_profile": "primary_plus_fallback",
        }
        if expected_runtime_identity is not None:
            pin["expected_runtime_identity"] = expected_runtime_identity
        if expected_model_identity is not None:
            pin["expected_model_identity"] = expected_model_identity
        return self.update_governance_policy(
            lambda policy: {
                **policy,
                "governed_surfaces": {
                    **policy["governed_surfaces"],
                    "allowlisted_surfaces": sorted(
                        set(policy["governed_surfaces"].get("allowlisted_surfaces", [])) | {surface_id}
                    ),
                },
                "surface_version_pins": [pin],
            }
        )

    def stage_tmux_capture(self, tmux_socket: str, tmux_pane: str, content: str) -> None:
        if content:
            subprocess.run(
                ["tmux", "-S", tmux_socket, "send-keys", "-t", tmux_pane, "-l", content],
                check=True,
                capture_output=True,
                text=True,
            )

    def capture_tmux_pane(self, tmux_socket: str, tmux_pane: str) -> str:
        return subprocess.run(
            ["tmux", "-S", tmux_socket, "capture-pane", "-p", "-t", tmux_pane],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def seed_active_task_with_lease_and_lock(
        self,
        *,
        task_id: str = "task-contract-close",
        lease_id: str = "lease-contract-close",
        worker_id: str = "worker-codex-contract",
    ) -> tuple[str, str]:
        self.seed_worker(worker_id)
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        self.seed_task(
            task_id=task_id,
            summary="Contract close slice",
            protected_surfaces=["docs/contract-close.md"],
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                "UPDATE tasks SET state = 'reserved' WHERE task_id = ?",
                (task_id,),
            )
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
                evidence_version="evidence-contract-close",
            ),
            EventRecord(
                event_id="evt-lease-contract-close",
                event_type="lease.activated",
                aggregate_type="lease",
                aggregate_id=lease_id,
                timestamp=self.iso_now(seconds_ago=4),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-lease-contract-close",
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
                event_id="evt-task-contract-close-active",
                event_type="task.activated",
                aggregate_type="task",
                aggregate_id=task_id,
                timestamp=self.iso_now(seconds_ago=3),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id="corr-task-contract-close-active",
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
                    "lock-contract-close",
                    "file",
                    "docs/contract-close.md",
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

    def seed_same_second_checkpoints(
        self,
        *,
        task_id: str,
        target_action: str,
        affected_refs: dict[str, object],
    ) -> tuple[str, str]:
        captured_at = self.iso_now()
        baseline_fingerprint = current_repo_fingerprint(self.repo_root)
        older_checkpoint_id = "checkpoint-zzzzzzzzzzzz"
        newer_checkpoint_id = "checkpoint-aaaaaaaaaaaa"
        self.insert_review_checkpoint(
            checkpoint_id=older_checkpoint_id,
            task_id=task_id,
            target_action=target_action,
            captured_at=captured_at,
            affected_refs=affected_refs,
            baseline_fingerprint=baseline_fingerprint,
        )
        self.insert_review_checkpoint(
            checkpoint_id=newer_checkpoint_id,
            task_id=task_id,
            target_action=target_action,
            captured_at=captured_at,
            affected_refs=affected_refs,
            baseline_fingerprint=baseline_fingerprint,
        )
        return older_checkpoint_id, newer_checkpoint_id

    def seed_interrupted_recovery_task(
        self,
        *,
        task_id: str = "task-contract-interrupted-recovery",
        recovery_run_id: str = "recovery-task-interrupted-contract",
        proposed_worker_id: str = "worker-contract-recovery-target",
    ) -> tuple[str, str]:
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id=task_id,
                title="Interrupted recovery slice",
                description="Interrupted recovery slice",
                workflow_class="implementation",
                intent="Interrupted recovery slice",
                required_capabilities=[],
                protected_surfaces=["docs/interrupted-recovery.md"],
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
                payload={"summary": "Interrupted recovery slice"},
                redaction_level="none",
            ),
        )

        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                "UPDATE tasks SET state = 'reconciliation', routing_policy_ref = ? WHERE task_id = ?",
                ("phase1-defaults-v1", task_id),
            )
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
                            "predecessor_worker_id": "worker-contract-predecessor",
                            "predecessor_lease_id": "lease-contract-predecessor",
                            "evidence_summary": {"source": "restart"},
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

    def test_task_help_lists_story_4_2_contract_verbs(self) -> None:
        result = self.run_cli("task", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)

        for verb in ("list", "create", "assign", "inspect", "close", "archive", "pause", "resume", "reroute", "abort"):
            self.assertIn(verb, result.stdout)

    def test_task_create_defaults_workflow_class_and_returns_contract_action_envelope(self) -> None:
        self.init_repo()

        result = self.run_cli("task", "create", "--summary", "Draft contract slice", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task create")
        self.assertIn("timestamp", payload)
        self.assertEqual(payload["warnings"], [])
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["data"]["result"]["task"]["summary"], "Draft contract slice")
        self.assertEqual(payload["data"]["result"]["task"]["workflow_class"], "implementation")
        self.assertEqual(payload["data"]["event"]["event_type"], "task.created")

    def test_task_create_uses_controller_default_workflow_class_from_repo_local_config(self) -> None:
        self.init_repo()

        controller_defaults_path = self.repo_root / ".codex" / "orchestration" / "controller-defaults.json"
        controller_defaults = json.loads(controller_defaults_path.read_text(encoding="utf-8"))
        controller_defaults["task"]["default_workflow_class"] = "review"
        controller_defaults_path.write_text(
            json.dumps(controller_defaults, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self.run_cli("task", "create", "--summary", "Use configured default", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["task"]["workflow_class"], "review")

    def test_task_assign_accepts_workflow_class_selector_and_returns_contract_action_envelope(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(protected_surfaces=["docs/contract-assign.md"])

        result = self.run_cli("task", "assign", "--task", task_id, "--workflow-class", "implementation", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task assign")
        self.assertIn("timestamp", payload)
        self.assertEqual(payload["warnings"], [])
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["data"]["result"]["selected_worker_id"], "worker-codex-contract")
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "policy_automatic")
        self.assertFalse(payload["data"]["result"]["decision_rights"]["confirmation_required"])
        self.assertTrue(payload["data"]["result"]["decision_rights"]["allowed"])
        self.assertEqual(payload["data"]["event"]["event_type"], "task.assigned")
        event_id = payload["data"]["event"]["event_id"]

        lease_id = payload["data"]["result"]["lease_id"]
        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "active")
        self.assertEqual(inspect_task_payload["task"]["current_worker_id"], "worker-codex-contract")
        self.assertEqual(inspect_task_payload["task"]["current_lease_id"], lease_id)

        inspect_lease_payload = json.loads(self.run_cli("lease", "inspect", "--lease", lease_id, "--json").stdout)
        self.assertEqual(inspect_lease_payload["data"]["lease"]["state"], "active")
        self.assertIsNotNone(inspect_lease_payload["data"]["lease"]["accepted_at"])

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "active")
        self.assertEqual(lock_payload["data"]["locks"][0]["task_id"], task_id)

        event_payload = json.loads(self.run_cli("event", "inspect", "--event", event_id, "--json").stdout)
        self.assertEqual(event_payload["data"]["event"]["event_type"], "task.assigned")

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        self.assertTrue(any(item["event_id"] == event_id for item in event_list_payload["data"]["events"]))

        overview_payload = json.loads(self.run_cli("overview", "show", "--json").stdout)
        self.assertEqual(overview_payload["data"]["overview"]["task_summary"]["active"], 1)
        self.assertEqual(overview_payload["data"]["overview"]["active_tasks"][0]["task_id"], task_id)

        pane_output = self.capture_tmux_pane(tmux_socket, tmux_pane)
        self.assertIn("MACS_TASK_ASSIGN", pane_output)
        self.assertIn(task_id, pane_output)

    def test_task_assign_accepts_explicit_worker_selector_and_reaches_active_state(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-assign-worker", protected_surfaces=["docs/contract-assign-worker.md"])

        result = self.run_cli("task", "assign", "--task", task_id, "--worker", "worker-codex-contract", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["result"]["selected_worker_id"], "worker-codex-contract")
        self.assertEqual(payload["data"]["result"]["task"]["state"], "active")

    def test_task_assign_rejects_unresolved_interrupted_recovery_run(self) -> None:
        self.init_repo()
        self.seed_worker(worker_id="worker-contract-recovery-target")
        task_id, recovery_run_id = self.seed_interrupted_recovery_task()

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-contract-recovery-target",
            "--json",
        )
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task assign")
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")
        self.assertIn(recovery_run_id, payload["errors"][0]["message"])
        self.assertIn("macs recovery retry", payload["errors"][0]["message"])

    def test_recovery_retry_resumes_interrupted_recovery_run_without_predecessor_lease(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-contract-recovery-target",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id, recovery_run_id = self.seed_interrupted_recovery_task()

        result = self.run_cli("recovery", "retry", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertFalse(payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])
        self.assertFalse(payload["data"]["result"]["controller_state_changed"])

        result = self.run_cli("recovery", "retry", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs recovery retry")
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(payload["data"]["result"]["task"]["current_worker_id"], "worker-contract-recovery-target")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertTrue(payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])
        self.assertEqual(payload["data"]["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(payload["data"]["recovery_run"]["state"], "completed")

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "active")
        self.assertEqual(inspect_payload["task"]["current_worker_id"], "worker-contract-recovery-target")
        self.assertEqual(inspect_payload["task"]["controller_truth"]["recovery_run"]["state"], "completed")

    def test_recovery_retry_keeps_reroute_events_attached_to_one_operator_decision(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        task_id, predecessor_lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-recovery-reroute-rationale",
            lease_id="lease-contract-recovery-reroute-rationale",
            worker_id="worker-recovery-reroute-predecessor",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        successor_worker_id = self.seed_worker_with_tmux(
            worker_id="worker-recovery-reroute-successor",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )

        disable_result = self.run_cli(
            "worker",
            "disable",
            "--worker",
            "worker-recovery-reroute-predecessor",
            "--json",
        )
        self.assertEqual(disable_result.returncode, 0, disable_result.stdout + disable_result.stderr)

        retry_result = self.run_cli(
            "recovery",
            "retry",
            "--task",
            task_id,
            "--confirm",
            "--rationale",
            "controller review confirmed successor reroute is safe",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "qa.retry@example.test"},
        )
        self.assertEqual(retry_result.returncode, 0, retry_result.stdout + retry_result.stderr)

        retry_payload = json.loads(retry_result.stdout)
        self.assertEqual(retry_payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(retry_payload["data"]["result"]["task"]["current_worker_id"], successor_worker_id)

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        decision_events = [
            item
            for item in event_list_payload["data"]["events"]
            if item["event_type"] == "intervention.decision_recorded"
            and item["aggregate_id"] == task_id
        ]
        self.assertEqual(len(decision_events), 1)
        decision_event = decision_events[0]
        self.assertEqual(decision_event["actor_id"], "qa.retry@example.test")
        self.assertEqual(
            decision_event["payload_summary"]["intervention_rationale"],
            "controller review confirmed successor reroute is safe",
        )

        retry_event = next(
            item
            for item in event_list_payload["data"]["events"]
            if item["event_type"] == "recovery.retry_requested"
            and item["aggregate_id"] == retry_payload["data"]["recovery_run"]["recovery_run_id"]
        )
        revoke_event = next(
            item
            for item in event_list_payload["data"]["events"]
            if item["event_type"] == "lease.revoked"
            and item["aggregate_id"] == predecessor_lease_id
        )
        lock_release_event = next(
            item
            for item in event_list_payload["data"]["events"]
            if item["event_type"] == "lock.released"
            and item["aggregate_id"] == task_id
        )
        reroute_event_id = retry_payload["data"]["event"]["event_id"]
        reroute_event = json.loads(self.run_cli("event", "inspect", "--event", reroute_event_id, "--json").stdout)["data"]["event"]

        self.assertEqual(retry_event["payload_summary"]["decision_event_id"], decision_event["event_id"])
        self.assertEqual(revoke_event["payload_summary"]["decision_event_id"], decision_event["event_id"])
        self.assertEqual(lock_release_event["payload_summary"]["decision_event_id"], decision_event["event_id"])
        self.assertEqual(reroute_event["payload"]["decision_event_id"], decision_event["event_id"])

    def test_recovery_retry_human_readable_reports_decision_rights_and_state_change(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-human-recovery-target",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id, _ = self.seed_interrupted_recovery_task(
            task_id="task-human-recovery-retry",
            recovery_run_id="recovery-human-retry",
            proposed_worker_id="worker-human-recovery-target",
        )

        result = self.run_cli("recovery", "retry", "--task", task_id, "--confirm")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Decision Rights: operator_confirmed", result.stdout)
        self.assertIn("Confirmation: confirmed", result.stdout)
        self.assertIn("Controller State Changed: yes", result.stdout)
        self.assertIn(f"Next Action: macs task inspect --task {task_id}", result.stdout)

    def test_recovery_reconcile_abandons_interrupted_recovery_and_allows_fresh_assignment(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        task_id, recovery_run_id = self.seed_interrupted_recovery_task(
            task_id="task-contract-interrupted-reconcile",
            recovery_run_id="recovery-task-interrupted-reconcile",
            proposed_worker_id="worker-contract-fresh-successor",
        )

        reconcile_result = self.run_cli("recovery", "reconcile", "--task", task_id, "--json")
        self.assertEqual(reconcile_result.returncode, 4, reconcile_result.stdout + reconcile_result.stderr)
        reconcile_payload = json.loads(reconcile_result.stdout)
        self.assertFalse(reconcile_payload["ok"])
        self.assertEqual(reconcile_payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(reconcile_payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertFalse(reconcile_payload["data"]["result"]["controller_state_changed"])

        reconcile_result = self.run_cli("recovery", "reconcile", "--task", task_id, "--confirm", "--json")
        self.assertEqual(reconcile_result.returncode, 0, reconcile_result.stdout + reconcile_result.stderr)
        reconcile_payload = json.loads(reconcile_result.stdout)
        self.assertTrue(reconcile_payload["ok"])
        self.assertEqual(reconcile_payload["command"], "macs recovery reconcile")
        self.assertEqual(reconcile_payload["data"]["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(reconcile_payload["data"]["recovery_run"]["state"], "abandoned")
        self.assertTrue(reconcile_payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])

        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-contract-fresh-successor",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        assign_result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-contract-fresh-successor",
            "--json",
        )
        self.assertEqual(assign_result.returncode, 0, assign_result.stdout + assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertTrue(assign_payload["ok"])
        self.assertEqual(assign_payload["data"]["result"]["task"]["state"], "active")

    def test_recovery_reconcile_records_operator_decision_event_and_rationale(self) -> None:
        self.init_repo()
        task_id, recovery_run_id = self.seed_interrupted_recovery_task(
            task_id="task-contract-interrupted-reconcile-rationale",
            recovery_run_id="recovery-task-interrupted-reconcile-rationale",
            proposed_worker_id="worker-contract-fresh-successor-rationale",
        )

        reconcile_result = self.run_cli(
            "recovery",
            "reconcile",
            "--task",
            task_id,
            "--confirm",
            "--rationale",
            "operator closed the interrupted run and requested a fresh assignment path",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "qa.reconcile@example.test"},
        )
        self.assertEqual(reconcile_result.returncode, 0, reconcile_result.stdout + reconcile_result.stderr)

        reconcile_payload = json.loads(reconcile_result.stdout)
        decision_event_id = reconcile_payload["data"]["event"]["payload"]["decision_event_id"]
        decision_payload = json.loads(self.run_cli("event", "inspect", "--event", decision_event_id, "--json").stdout)
        decision_event = decision_payload["data"]["event"]

        self.assertEqual(reconcile_payload["data"]["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(reconcile_payload["data"]["recovery_run"]["state"], "abandoned")
        self.assertEqual(decision_event["actor_id"], "qa.reconcile@example.test")
        self.assertEqual(decision_event["payload"]["decision_action"], "recovery_reconcile")
        self.assertEqual(
            decision_event["payload"]["intervention_rationale"],
            "operator closed the interrupted run and requested a fresh assignment path",
        )

    def test_task_pause_transitions_active_task_to_intervention_hold_without_replacing_live_lease(self) -> None:
        self.init_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-pause",
            lease_id="lease-contract-pause",
            worker_id="worker-pause-owner",
        )

        result = self.run_cli("task", "pause", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertFalse(payload["data"]["result"]["controller_state_changed"])

        result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task pause")
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "intervention_hold")
        self.assertEqual(payload["data"]["result"]["task"]["current_worker_id"], "worker-pause-owner")
        self.assertEqual(payload["data"]["result"]["task"]["current_lease_id"], lease_id)
        self.assertEqual(payload["data"]["result"]["lease"]["lease_id"], lease_id)
        self.assertEqual(payload["data"]["result"]["lease"]["state"], "paused")
        self.assertEqual(payload["data"]["result"]["lease"]["intervention_reason"], "operator_pause")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertTrue(payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])
        self.assertEqual(payload["data"]["event"]["event_type"], "task.paused")
        self.assertTrue(
            any("does not advertise pause/resume depth" in warning for warning in payload["warnings"]),
            payload["warnings"],
        )

        inspect_lease_payload = json.loads(self.run_cli("lease", "inspect", "--lease", lease_id, "--json").stdout)
        self.assertEqual(inspect_lease_payload["data"]["lease"]["state"], "paused")
        self.assertEqual(inspect_lease_payload["data"]["lease"]["intervention_reason"], "operator_pause")

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(len(lease_history_payload["data"]["leases"]), 1)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["lease_id"], lease_id)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "paused")

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "active")
        self.assertEqual(lock_payload["data"]["locks"][0]["lease_id"], lease_id)

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("lease.paused", event_types)
        self.assertIn("task.paused", event_types)

    def test_task_pause_records_operator_decision_event_and_causation_with_rationale(self) -> None:
        self.init_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-pause-rationale",
            lease_id="lease-contract-pause-rationale",
            worker_id="worker-pause-rationale-owner",
        )

        result = self.run_cli(
            "task",
            "pause",
            "--task",
            task_id,
            "--confirm",
            "--rationale",
            "unsafe output observed during manual review",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "qa.operator@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["event"]["event_type"], "task.paused")
        decision_event_id = payload["data"]["event"]["payload"]["decision_event_id"]

        decision_payload = json.loads(self.run_cli("event", "inspect", "--event", decision_event_id, "--json").stdout)
        decision_event = decision_payload["data"]["event"]
        self.assertEqual(decision_event["event_type"], "intervention.decision_recorded")
        self.assertEqual(decision_event["actor_type"], "operator")
        self.assertEqual(decision_event["actor_id"], "qa.operator@example.test")
        self.assertEqual(decision_event["payload"]["decision_action"], "pause")
        self.assertEqual(
            decision_event["payload"]["intervention_rationale"],
            "unsafe output observed during manual review",
        )
        self.assertEqual(decision_event["payload"]["affected_refs"]["task_id"], task_id)
        self.assertEqual(decision_event["payload"]["affected_refs"]["lease_id"], lease_id)
        self.assertEqual(payload["data"]["event"]["payload"]["intervention_rationale"], decision_event["payload"]["intervention_rationale"])

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        listed_decision = next(
            item
            for item in event_list_payload["data"]["events"]
            if item["event_id"] == decision_event_id
        )
        self.assertEqual(listed_decision["actor_id"], "qa.operator@example.test")
        self.assertEqual(
            listed_decision["payload_summary"]["intervention_rationale"],
            "unsafe output observed during manual review",
        )

    def test_task_assign_rejects_non_allowlisted_governed_surface_and_preserves_failed_routing_context(self) -> None:
        self.init_repo()
        self.seed_worker_row(
            worker_id="worker-codex-governed",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
        )
        task_id = self.seed_task(task_id="task-contract-governed-route", summary="Governed route")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("governance policy rejected governed surfaces", payload["data"]["result"]["blocking_condition"])
        self.assertIn("governance-policy.json", payload["data"]["result"]["next_action"])
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertEqual(rejected["worker_id"], "worker-codex-governed")
        self.assertIn("governed_surface_not_allowlisted:mcp", rejected["reasons"])

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "pending_assignment")
        self.assertEqual(
            inspect_payload["task"]["blocking_condition"],
            "governance policy rejected governed surfaces for the available workers",
        )
        self.assertIn(
            "governed_surface_not_allowlisted:mcp",
            inspect_payload["task"]["routing_decision"]["rationale"]["rejected_workers"][0]["reasons"],
        )

    def test_task_assign_rejects_surface_version_pin_mismatch_and_preserves_routing_context(self) -> None:
        self.init_repo()
        self.configure_surface_version_pin(
            adapter_id="codex",
            expected_runtime_identity="codex",
            expected_model_identity="gpt-5.4",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.stage_tmux_capture(
            tmux_socket,
            tmux_pane,
            "codex --model gpt-5.4-mini --sandbox workspace-write --yolo",
        )
        self.seed_worker_row(
            worker_id="worker-codex-version-mismatch",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-version-mismatch", summary="Version mismatch")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("surface version pin enforcement rejected the available workers", payload["data"]["result"]["blocking_condition"])
        self.assertIn("mismatch", payload["data"]["result"]["blocking_condition"])
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertIn("surface_version_pin_mismatch:mcp", rejected["reasons"])
        blocked = rejected["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_pin_mismatch")
        self.assertEqual(blocked["observed"]["model_identity"]["identity"], "gpt-5.4-mini")

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertIn("mismatch", inspect_payload["task"]["blocking_condition"])
        self.assertIn(
            "surface_version_pin_mismatch:mcp",
            inspect_payload["task"]["routing_decision"]["rationale"]["rejected_workers"][0]["reasons"],
        )

    def test_task_assign_rejects_missing_surface_version_evidence_and_preserves_routing_context(self) -> None:
        self.init_repo()
        self.configure_surface_version_pin(
            adapter_id="claude",
            expected_runtime_identity="claude",
            expected_model_identity="claude-3-7-sonnet",
        )
        task_id = self.seed_task(task_id="task-contract-version-missing", summary="Version missing")
        self.seed_worker_row(
            worker_id="worker-claude-version-missing",
            runtime_type="claude",
            adapter_id="claude",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
        )

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("missing evidence", payload["data"]["result"]["blocking_condition"])
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertIn("surface_version_evidence_missing:mcp", rejected["reasons"])
        blocked = rejected["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_evidence_missing")
        self.assertIsNone(blocked["observed"]["model_identity"])

    def test_task_assign_rejects_stale_surface_version_evidence_and_preserves_routing_context(self) -> None:
        self.init_repo()
        self.configure_surface_version_pin(
            adapter_id="claude",
            expected_runtime_identity="claude",
        )
        self.seed_worker_row(
            worker_id="worker-claude-version-stale",
            runtime_type="claude",
            adapter_id="claude",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            freshness_seconds=120,
        )
        task_id = self.seed_task(task_id="task-contract-version-stale", summary="Version stale")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("stale evidence", payload["data"]["result"]["blocking_condition"])
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertIn("surface_version_evidence_stale:mcp", rejected["reasons"])
        blocked = rejected["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_evidence_stale")
        self.assertGreaterEqual(blocked["observed"]["runtime_identity"]["freshness_seconds"], 120)

    def test_task_assign_rejects_low_trust_surface_version_evidence_and_preserves_routing_context(self) -> None:
        self.init_repo()
        self.configure_surface_version_pin(
            adapter_id="codex",
            expected_runtime_identity="codex",
            expected_model_identity="gpt-5.4",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.stage_tmux_capture(tmux_socket, tmux_pane, "idle shell prompt")
        self.seed_worker_row(
            worker_id="worker-codex-version-untrusted",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-version-untrusted", summary="Version untrusted")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("low-trust evidence", payload["data"]["result"]["blocking_condition"])
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertIn("surface_version_evidence_untrusted:mcp", rejected["reasons"])
        blocked = rejected["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_evidence_untrusted")
        self.assertEqual(blocked["observed"]["model_identity"]["confidence"], "low")

    def test_task_assign_rejects_out_of_scope_secret_selector_before_assignment_state(self) -> None:
        self.init_repo()
        self.configure_secret_scopes(
            [
                {
                    "surface_id": "mcp",
                    "adapter_id": "claude",
                    "workflow_class": "review",
                    "operating_profile": "primary_plus_fallback",
                    "secret_ref": "mcp.claude.token",
                    "display_name": "Claude MCP token",
                    "redaction_label": "masked",
                }
            ]
        )
        self.seed_worker_row(
            worker_id="worker-codex-secret-no-scope",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
        )
        task_id = self.seed_task(task_id="task-contract-secret-no-scope", summary="Secret no-scope block")

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-codex-secret-no-scope",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        secret_resolution = payload["data"]["result"]["secret_resolution"]
        self.assertEqual(secret_resolution["status"], "blocked")
        self.assertEqual(secret_resolution["reason"], "secret_scope_selector_mismatch")
        self.assertEqual(secret_resolution["surface_summaries"][0]["reason"], "secret_scope_selector_mismatch")
        self.assertEqual(payload["data"]["result"]["affected_refs"]["surface_id"], "mcp")
        self.assertIn("did not match the selected adapter", payload["data"]["result"]["blocking_condition"])

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["task"]["current_worker_id"])
        self.assertIsNone(inspect_payload["task"]["current_lease_id"])
        self.assertEqual(inspect_payload["task"]["secret_resolution"]["reason"], "secret_scope_selector_mismatch")

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(lease_history_payload["data"]["leases"], [])

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("routing.decision_recorded", event_types)
        self.assertNotIn("task.assigned", event_types)

    def test_task_assign_rejects_unresolved_secret_ref_before_assignment_and_lease_reservation(self) -> None:
        self.init_repo()
        self.configure_secret_scopes(
            [
                {
                    "surface_id": "mcp",
                    "adapter_id": "codex",
                    "workflow_class": "implementation",
                    "operating_profile": "primary_plus_fallback",
                    "secret_ref": "mcp.codex.token",
                    "display_name": "Codex MCP token",
                    "redaction_label": "masked",
                }
            ]
        )
        self.seed_worker_row(
            worker_id="worker-codex-secret-unresolved",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
        )
        task_id = self.seed_task(task_id="task-contract-secret-unresolved", summary="Secret unresolved block")

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-codex-secret-unresolved",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        secret_resolution = payload["data"]["result"]["secret_resolution"]
        self.assertEqual(secret_resolution["status"], "blocked")
        self.assertEqual(secret_resolution["reason"], "secret_ref_unresolved")
        self.assertEqual(secret_resolution["surface_summaries"][0]["unresolved_secret_refs"], ["mcp.codex.token"])
        self.assertEqual(payload["data"]["result"]["affected_refs"]["secret_ref"], "mcp.codex.token")
        self.assertIn("could not be resolved", payload["data"]["result"]["blocking_condition"])

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["task"]["current_worker_id"])
        self.assertIsNone(inspect_payload["task"]["current_lease_id"])
        self.assertEqual(inspect_payload["task"]["secret_resolution"]["reason"], "secret_ref_unresolved")

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("routing.decision_recorded", event_types)
        self.assertNotIn("task.assigned", event_types)

    def test_task_assign_resolves_secret_only_for_selected_worker_and_keeps_raw_values_out_of_audit(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        runtime_secret = os.urandom(8).hex()
        self.write_worker_env({"MCP_CODEX_TOKEN": runtime_secret})
        self.configure_secret_scopes(
            [
                {
                    "surface_id": "mcp",
                    "adapter_id": "codex",
                    "workflow_class": "implementation",
                    "operating_profile": "primary_plus_fallback",
                    "secret_ref": "mcp.codex.token",
                    "display_name": "Codex MCP token",
                    "redaction_label": "masked",
                },
                {
                    "surface_id": "mcp",
                    "adapter_id": "claude",
                    "workflow_class": "implementation",
                    "operating_profile": "primary_plus_fallback",
                    "secret_ref": "mcp.claude.token",
                    "display_name": "Claude MCP token",
                    "redaction_label": "masked",
                },
            ]
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_row(
            worker_id="worker-codex-secret-selected",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        self.seed_worker_row(
            worker_id="worker-claude-secret-unselected",
            runtime_type="claude",
            adapter_id="claude",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
        )
        task_id = self.seed_task(task_id="task-contract-secret-selected", summary="Secret selected-worker resolution")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["selected_worker_id"], "worker-codex-secret-selected")
        secret_resolution = payload["data"]["result"]["secret_resolution"]
        self.assertEqual(secret_resolution["status"], "resolved")
        self.assertEqual(secret_resolution["required_secret_refs"], ["mcp.codex.token"])
        self.assertEqual(secret_resolution["resolved_secret_refs"], ["mcp.codex.token"])
        self.assertNotIn(runtime_secret, json.dumps(secret_resolution, sort_keys=True))
        self.assertNotIn("mcp.claude.token", json.dumps(secret_resolution, sort_keys=True))

        assignment_event = payload["data"]["event"]
        self.assertIn("secret_resolution", assignment_event["payload"])
        self.assertNotIn(runtime_secret, json.dumps(assignment_event["payload"]["secret_resolution"], sort_keys=True))
        self.assertNotIn("resolved_secrets", json.dumps(assignment_event["payload"], sort_keys=True))

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["secret_resolution"]["resolved_secret_refs"], ["mcp.codex.token"])
        self.assertNotIn(runtime_secret, inspect_payload["task"]["blocking_condition"] or "")

        event_payload = json.loads(
            self.run_cli("event", "inspect", "--event", assignment_event["event_id"], "--json").stdout
        )
        self.assertEqual(
            event_payload["data"]["event"]["payload"]["secret_resolution"]["resolved_secret_refs"],
            ["mcp.codex.token"],
        )
        self.assertNotIn(runtime_secret, json.dumps(event_payload["data"]["event"], sort_keys=True))

        pane_output = self.capture_tmux_pane(tmux_socket, tmux_pane)
        self.assertIn("MACS_TASK_ASSIGN", pane_output)
        self.assertNotIn(runtime_secret, pane_output)
        self.assertNotIn("mcp.codex.token", pane_output)

    def test_task_assign_keeps_non_governed_or_non_secret_backed_paths_unchanged(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        self.configure_secret_scopes(
            [
                {
                    "surface_id": "mcp",
                    "adapter_id": "codex",
                    "workflow_class": "implementation",
                    "operating_profile": "primary_plus_fallback",
                    "secret_ref": "mcp.codex.token",
                    "display_name": "Codex MCP token",
                    "redaction_label": "masked",
                }
            ]
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_row(
            worker_id="worker-codex-no-governed-surface",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered"],
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-secret-not-required", summary="Secret not required")

        result = self.run_cli(
            "task",
            "assign",
            "--task",
            task_id,
            "--worker",
            "worker-codex-no-governed-surface",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(payload["data"]["result"]["secret_resolution"]["status"], "not_required")

    def test_adapter_inspect_surfaces_repo_local_settings(self) -> None:
        self.init_repo()
        self.update_adapter_settings(
            lambda settings: {
                **settings,
                "adapters": {
                    **settings["adapters"],
                    "codex": {
                        **settings["adapters"]["codex"],
                        "enabled": False,
                        "notes": "disabled for repo-local validation",
                    },
                },
            }
        )

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["data"]["adapter"]["settings"]["enabled"])
        self.assertEqual(
            payload["data"]["adapter"]["settings"]["notes"],
            "disabled for repo-local validation",
        )

    def test_worker_register_rejects_disabled_adapter_from_repo_local_settings(self) -> None:
        self.init_repo()
        self.seed_worker_row(
            worker_id="worker-register-disabled",
            runtime_type="codex",
            adapter_id="local",
            capabilities=["implementation"],
            state="registered",
        )
        self.update_adapter_settings(
            lambda settings: {
                **settings,
                "adapters": {
                    **settings["adapters"],
                    "codex": {
                        **settings["adapters"]["codex"],
                        "enabled": False,
                    },
                },
            }
        )

        result = self.run_cli("worker", "register", "--worker", "worker-register-disabled", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("disabled by repo-local adapter settings", payload["error"]["message"])

    def test_task_assign_rejects_disabled_adapter_and_preserves_failed_routing_context(self) -> None:
        self.init_repo()
        self.seed_worker_row(
            worker_id="worker-codex-disabled",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
        )
        self.seed_task(task_id="task-contract-disabled-adapter", summary="Disabled adapter route")
        self.update_adapter_settings(
            lambda settings: {
                **settings,
                "adapters": {
                    **settings["adapters"],
                    "codex": {
                        **settings["adapters"]["codex"],
                        "enabled": False,
                    },
                },
            }
        )

        result = self.run_cli("task", "assign", "--task", "task-contract-disabled-adapter", "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        rejected = payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertEqual(rejected["worker_id"], "worker-codex-disabled")
        self.assertIn("adapter_disabled", rejected["reasons"])

    def test_task_assign_omits_prompt_content_from_assignment_event_by_default(self) -> None:
        self.init_repo()
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-codex-audit-default",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-audit-default", summary="Audit default omit")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)

        event = payload["data"]["event"]
        self.assertEqual(event["redaction_level"], "omitted")
        self.assertEqual(event["payload"]["audit_content"]["prompt_content"]["status"], "omitted")
        self.assertNotIn("value", event["payload"]["audit_content"]["prompt_content"])

    def test_task_assign_can_retain_prompt_content_when_governance_policy_allows_it(self) -> None:
        self.init_repo()
        self.update_governance_policy(
            lambda policy: {
                **policy,
                "audit_content": {
                    **policy["audit_content"],
                    "prompt_content": {"mode": "retain"},
                },
            }
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-codex-audit-retain",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-audit-retain", summary="Audit retain")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)

        event = payload["data"]["event"]
        self.assertEqual(event["redaction_level"], "none")
        retained = event["payload"]["audit_content"]["prompt_content"]
        self.assertEqual(retained["status"], "retained")
        self.assertIn("MACS_TASK_ASSIGN", retained["value"])

    def test_task_assign_allows_pinned_governed_surface_for_matching_adapter(self) -> None:
        self.init_repo()
        self.update_governance_policy(
            lambda policy: {
                **policy,
                "governed_surfaces": {
                    **policy["governed_surfaces"],
                    "allowlisted_surfaces": ["mcp"],
                    "pinned_surfaces": {"mcp": ["codex"]},
                },
            }
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-codex-governed-pinned",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            existing_tags = conn.execute(
                "SELECT operator_tags FROM workers WHERE worker_id = ?",
                ("worker-codex-governed-pinned",),
            ).fetchone()
            self.assertIsNotNone(existing_tags)
            tags = json.loads(existing_tags[0])
            tags.append("surface:mcp")
            conn.execute(
                "UPDATE workers SET operator_tags = ? WHERE worker_id = ?",
                (json.dumps(sorted(tags)), "worker-codex-governed-pinned"),
            )
            conn.commit()
        finally:
            conn.close()

        task_id = self.seed_task(task_id="task-contract-governed-pinned", summary="Governed pin allow")
        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["selected_worker_id"], "worker-codex-governed-pinned")
        allowed = payload["data"]["result"]["routing_decision"]["rationale"]["ranked_candidates"][0]["governance"]["allowed_surfaces"]
        self.assertEqual(allowed[0]["surface_id"], "mcp")

    def test_task_assign_can_redact_prompt_content_when_governance_policy_requests_it(self) -> None:
        self.init_repo()
        self.update_governance_policy(
            lambda policy: {
                **policy,
                "audit_content": {
                    **policy["audit_content"],
                    "prompt_content": {"mode": "redact"},
                },
            }
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-codex-audit-redact",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        task_id = self.seed_task(task_id="task-contract-audit-redact", summary="Audit redact")

        result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)

        event = payload["data"]["event"]
        self.assertEqual(event["redaction_level"], "redacted")
        redacted = event["payload"]["audit_content"]["prompt_content"]
        self.assertEqual(redacted["status"], "redacted")
        self.assertNotIn("value", redacted)

    def test_task_resume_restores_operator_paused_task_on_same_lease(self) -> None:
        self.init_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-resume",
            lease_id="lease-contract-resume",
            worker_id="worker-resume-owner",
        )

        pause_result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(pause_result.returncode, 0, pause_result.stdout + pause_result.stderr)

        result = self.run_cli("task", "resume", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertFalse(payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])

        result = self.run_cli("task", "resume", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task resume")
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "active")
        self.assertEqual(payload["data"]["result"]["task"]["current_worker_id"], "worker-resume-owner")
        self.assertEqual(payload["data"]["result"]["task"]["current_lease_id"], lease_id)
        self.assertEqual(payload["data"]["result"]["lease"]["lease_id"], lease_id)
        self.assertEqual(payload["data"]["result"]["lease"]["state"], "active")
        self.assertIsNone(payload["data"]["result"]["lease"]["intervention_reason"])
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertTrue(payload["data"]["result"]["decision_rights"]["operator_confirmation_received"])
        self.assertEqual(payload["data"]["event"]["event_type"], "task.resumed")
        self.assertTrue(
            any("does not advertise pause/resume depth" in warning for warning in payload["warnings"]),
            payload["warnings"],
        )

        inspect_lease_payload = json.loads(self.run_cli("lease", "inspect", "--lease", lease_id, "--json").stdout)
        self.assertEqual(inspect_lease_payload["data"]["lease"]["state"], "active")
        self.assertIsNone(inspect_lease_payload["data"]["lease"]["intervention_reason"])

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(len(lease_history_payload["data"]["leases"]), 1)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["lease_id"], lease_id)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "active")

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("lease.resumed", event_types)
        self.assertIn("task.resumed", event_types)

    def test_task_pause_rejects_task_without_live_lease(self) -> None:
        self.init_repo()
        task_id = self.seed_task(task_id="task-contract-pause-conflict")

        result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task pause")
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertIsNone(payload["data"]["event"])

    def test_task_resume_rejects_task_that_is_not_operator_paused(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-resume-conflict",
            lease_id="lease-contract-resume-conflict",
            worker_id="worker-resume-conflict",
        )

        result = self.run_cli("task", "resume", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task resume")
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertIsNone(payload["data"]["event"])

    def test_task_resume_rejects_degraded_owner_with_explicit_precondition_error(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-resume-degraded",
            lease_id="lease-contract-resume-degraded",
            worker_id="worker-resume-degraded",
        )
        pause_result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(pause_result.returncode, 0, pause_result.stdout + pause_result.stderr)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute("UPDATE workers SET state = 'degraded' WHERE worker_id = ?", ("worker-resume-degraded",))
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli("task", "resume", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task resume")
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")
        self.assertIn("inspect", payload["errors"][0]["message"])
        self.assertIsNone(payload["data"]["event"])

    def test_task_resume_rejects_when_startup_reconciliation_blocks_progress(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-resume-blocked",
            lease_id="lease-contract-resume-blocked",
            worker_id="worker-resume-blocked",
        )
        pause_result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(pause_result.returncode, 0, pause_result.stdout + pause_result.stderr)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO metadata(key, value) VALUES('assignments_blocked', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli("task", "resume", "--task", task_id, "--confirm", "--json")
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task resume")
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")
        self.assertIn("startup recovery reconciliation", payload["errors"][0]["message"])
        self.assertIsNone(payload["data"]["event"])

    def test_overview_reclassifies_stale_current_owner_and_freezes_active_task_without_new_lease(self) -> None:
        self.init_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-freeze-stale-owner",
            lease_id="lease-contract-freeze-stale-owner",
            worker_id="worker-freeze-stale-owner",
        )

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                UPDATE workers
                SET tmux_socket = ?, tmux_session = ?, tmux_pane = ?
                WHERE worker_id = ?
                """,
                (tmux_socket, tmux_session, tmux_pane, "worker-freeze-stale-owner"),
            )
            conn.execute(
                """
                UPDATE workers
                SET last_evidence_at = ?, last_heartbeat_at = ?
                WHERE worker_id = ?
                """,
                (
                    self.iso_now(seconds_ago=120),
                    self.iso_now(seconds_ago=120),
                    "worker-freeze-stale-owner",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stdout + overview_result.stderr)

        overview_payload = json.loads(overview_result.stdout)
        self.assertEqual(overview_payload["data"]["health_changes"][0]["next_state"], "degraded")
        self.assertEqual(overview_payload["data"]["overview"]["task_summary"]["intervention_hold"], 1)
        self.assertEqual(overview_payload["data"]["overview"]["active_tasks"][0]["task_id"], task_id)

        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(inspect_task_payload["task"]["current_worker_id"], "worker-freeze-stale-owner")
        self.assertEqual(inspect_task_payload["task"]["current_lease_id"], lease_id)
        self.assertEqual(inspect_task_payload["task"]["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(
            inspect_task_payload["task"]["controller_truth"]["current_lease"]["intervention_reason"],
            "worker_state_degraded",
        )
        self.assertEqual(
            inspect_task_payload["task"]["next_action"],
            f"reroute or recover task {task_id} before resume",
        )

        inspect_lease_payload = json.loads(self.run_cli("lease", "inspect", "--lease", lease_id, "--json").stdout)
        self.assertEqual(inspect_lease_payload["data"]["lease"]["state"], "suspended")
        self.assertEqual(
            inspect_lease_payload["data"]["lease"]["intervention_reason"],
            "worker_state_degraded",
        )

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(len(lease_history_payload["data"]["leases"]), 1)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["lease_id"], lease_id)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "suspended")

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "active")
        self.assertEqual(lock_payload["data"]["locks"][0]["lease_id"], lease_id)

        event_list_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_list_payload["data"]["events"]]
        self.assertIn("lease.suspended", event_types)
        self.assertIn("task.risk_hold_applied", event_types)

    def test_worker_disable_freezes_owned_active_task_without_new_lease(self) -> None:
        self.init_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-freeze-disabled-owner",
            lease_id="lease-contract-freeze-disabled-owner",
            worker_id="worker-freeze-disabled-owner",
        )

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                UPDATE workers
                SET tmux_socket = ?, tmux_session = ?, tmux_pane = ?
                WHERE worker_id = ?
                """,
                (tmux_socket, tmux_session, tmux_pane, "worker-freeze-disabled-owner"),
            )
            conn.commit()
        finally:
            conn.close()

        disable_result = self.run_cli("worker", "disable", "--worker", "worker-freeze-disabled-owner", "--json")
        self.assertEqual(disable_result.returncode, 0, disable_result.stdout + disable_result.stderr)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            recovery_row = conn.execute(
                """
                SELECT state, decision_summary
                FROM recovery_runs
                WHERE task_id = ?
                ORDER BY started_at DESC, recovery_run_id DESC
                LIMIT 1
                """,
                (task_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(recovery_row)
        self.assertEqual(recovery_row[0], "pending_operator_action")
        self.assertIn("task inspect", recovery_row[1])

        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "intervention_hold")
        self.assertEqual(inspect_task_payload["task"]["current_lease_id"], lease_id)
        self.assertEqual(inspect_task_payload["task"]["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(
            inspect_task_payload["task"]["controller_truth"]["current_lease"]["intervention_reason"],
            "worker_state_unavailable",
        )

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(len(lease_history_payload["data"]["leases"]), 1)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "suspended")

    def test_task_reroute_revokes_predecessor_before_successor_activation(self) -> None:
        self.init_repo()
        task_id, predecessor_lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-reroute",
            lease_id="lease-contract-reroute-predecessor",
            worker_id="worker-reroute-predecessor",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        successor_worker_id = self.seed_worker_with_tmux(
            worker_id="worker-reroute-successor",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )

        disable_result = self.run_cli("worker", "disable", "--worker", "worker-reroute-predecessor", "--json")
        self.assertEqual(disable_result.returncode, 0, disable_result.stdout + disable_result.stderr)

        result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            successor_worker_id,
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")

        result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            successor_worker_id,
            "--confirm",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task reroute")
        self.assertEqual(payload["errors"], [])
        self.assertEqual(payload["warnings"], [])

        action = payload["data"]["result"]
        self.assertEqual(action["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertTrue(action["decision_rights"]["operator_confirmation_received"])
        task = action["task"]
        successor_lease_id = action["lease_id"]
        self.assertEqual(task["task_id"], task_id)
        self.assertEqual(task["state"], "active")
        self.assertEqual(task["current_worker_id"], successor_worker_id)
        self.assertEqual(task["current_lease_id"], successor_lease_id)
        self.assertNotEqual(successor_lease_id, predecessor_lease_id)

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        leases_by_id = {
            lease["lease_id"]: lease
            for lease in lease_history_payload["data"]["leases"]
        }
        self.assertEqual(leases_by_id[predecessor_lease_id]["state"], "replaced")
        self.assertEqual(leases_by_id[predecessor_lease_id]["replacement_lease_id"], successor_lease_id)
        self.assertEqual(leases_by_id[successor_lease_id]["state"], "active")
        self.assertEqual(leases_by_id[successor_lease_id]["worker_id"], successor_worker_id)

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        active_locks = [lock for lock in lock_payload["data"]["locks"] if lock["state"] == "active"]
        released_locks = [lock for lock in lock_payload["data"]["locks"] if lock["state"] == "released"]
        self.assertEqual(len(active_locks), 1)
        self.assertEqual(active_locks[0]["lease_id"], successor_lease_id)
        self.assertEqual(len(released_locks), 1)
        self.assertEqual(released_locks[0]["lease_id"], predecessor_lease_id)

        event_payload = json.loads(self.run_cli("event", "list", "--json").stdout)
        event_types = [item["event_type"] for item in event_payload["data"]["events"]]
        self.assertIn("lease.revoked", event_types)
        self.assertIn("lease.replaced", event_types)

    def test_task_reroute_records_operator_decision_event_and_rationale(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        task_id, predecessor_lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-reroute-rationale",
            lease_id="lease-contract-reroute-rationale",
            worker_id="worker-reroute-rationale-predecessor",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        successor_worker_id = self.seed_worker_with_tmux(
            worker_id="worker-reroute-rationale-successor",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )

        disable_result = self.run_cli("worker", "disable", "--worker", "worker-reroute-rationale-predecessor", "--json")
        self.assertEqual(disable_result.returncode, 0, disable_result.stdout + disable_result.stderr)

        reroute_result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            successor_worker_id,
            "--confirm",
            "--rationale",
            "manual controller review approved successor handoff",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "qa.reroute@example.test"},
        )
        self.assertEqual(reroute_result.returncode, 0, reroute_result.stdout + reroute_result.stderr)

        reroute_payload = json.loads(reroute_result.stdout)
        reroute_event = reroute_payload["data"]["event"]
        decision_event_id = reroute_event["payload"]["decision_event_id"]
        decision_payload = json.loads(self.run_cli("event", "inspect", "--event", decision_event_id, "--json").stdout)
        decision_event = decision_payload["data"]["event"]

        self.assertEqual(decision_event["actor_id"], "qa.reroute@example.test")
        self.assertEqual(decision_event["payload"]["decision_action"], "reroute")
        self.assertEqual(
            decision_event["payload"]["intervention_rationale"],
            "manual controller review approved successor handoff",
        )
        self.assertEqual(reroute_event["payload"]["decision_event_id"], decision_event_id)
        self.assertEqual(reroute_event["payload"]["previous_lease_id"], predecessor_lease_id)

    def test_task_reroute_rejects_active_task_without_recovery_state(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-reroute-active",
            lease_id="lease-contract-reroute-active",
            worker_id="worker-reroute-active",
        )
        self.seed_worker(worker_id="worker-reroute-active-target")

        result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            "worker-reroute-active-target",
            "--confirm",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task reroute")
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertIn("not reroutable from state active", payload["errors"][0]["message"])

    def test_task_reroute_bypasses_general_assignment_block_during_explicit_recovery(self) -> None:
        self.init_repo()
        task_id, predecessor_lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-reroute-startup",
            lease_id="lease-contract-reroute-startup",
            worker_id="worker-reroute-startup",
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        successor_worker_id = self.seed_worker_with_tmux(
            worker_id="worker-reroute-startup-target",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute("UPDATE tasks SET state = 'reconciliation' WHERE task_id = ?", (task_id,))
            conn.execute(
                """
                UPDATE leases
                SET state = 'suspended', intervention_reason = 'startup_recovery'
                WHERE lease_id = ?
                """,
                (predecessor_lease_id,),
            )
            conn.execute(
                """
                INSERT INTO metadata(key, value) VALUES('assignments_blocked', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            successor_worker_id,
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")

        result = self.run_cli(
            "task",
            "reroute",
            "--task",
            task_id,
            "--worker",
            successor_worker_id,
            "--confirm",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["result"]["task"]["current_worker_id"], successor_worker_id)

    def test_remaining_deferred_task_verbs_return_structured_unsupported_errors(self) -> None:
        deferred_commands = [
            ("abort", ["--task", "task-deferred"]),
        ]

        for verb, extra_args in deferred_commands:
            with self.subTest(verb=verb):
                result = self.run_cli("task", verb, *extra_args, "--json")
                self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["command"], f"macs task {verb}")
                self.assertIn("timestamp", payload)
                self.assertEqual(payload["warnings"], [])
                self.assertEqual(payload["errors"][0]["code"], "unsupported")
                self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
                self.assertFalse(payload["data"]["result"]["controller_state_changed"])
                self.assertIsNone(payload["data"]["event"])

    def test_lock_override_and_release_are_explicitly_guarded_in_phase1(self) -> None:
        self.init_repo()
        self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-lock-guard",
            lease_id="lease-contract-lock-guard",
            worker_id="worker-lock-guard",
        )
        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        lock_id = lock_payload["data"]["locks"][0]["lock_id"]

        for verb in ("override", "release"):
            with self.subTest(verb=verb):
                result = self.run_cli("lock", verb, "--lock", lock_id, "--json")
                self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["command"], f"macs lock {verb}")
                self.assertEqual(payload["errors"][0]["code"], "unsupported")
                self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
                self.assertFalse(payload["data"]["result"]["controller_state_changed"])
                self.assertEqual(payload["data"]["result"]["affected_refs"]["lock_id"], lock_id)

    def test_task_assign_blocked_by_recovery_returns_degraded_precondition(self) -> None:
        self.init_repo()
        self.seed_worker()
        task_id = self.seed_task(task_id="task-contract-assign-blocked")

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute(
                """
                INSERT INTO metadata(key, value) VALUES('assignments_blocked', '1')
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """
            )
            conn.commit()
        finally:
            conn.close()

        result = self.run_cli("task", "assign", "--task", task_id, "--worker", "worker-codex-contract", "--json")
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task assign")
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")

    def test_task_assign_rejects_stale_or_degraded_worker(self) -> None:
        for mode in ("stale", "degraded"):
            with self.subTest(mode=mode):
                self.init_repo()
                worker_id = self.seed_worker(worker_id=f"worker-{mode}-contract")
                task_id = self.seed_task(task_id=f"task-{mode}-contract")

                state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
                conn = sqlite3.connect(state_db)
                try:
                    if mode == "stale":
                        conn.execute(
                            """
                            UPDATE workers
                            SET last_evidence_at = ?, last_heartbeat_at = ?
                            WHERE worker_id = ?
                            """,
                            (self.iso_now(seconds_ago=120), self.iso_now(seconds_ago=120), worker_id),
                        )
                    else:
                        conn.execute("UPDATE workers SET state = 'degraded' WHERE worker_id = ?", (worker_id,))
                    conn.commit()
                finally:
                    conn.close()

                result = self.run_cli("task", "assign", "--task", task_id, "--worker", worker_id, "--json")
                self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["command"], "macs task assign")
                self.assertEqual(payload["errors"][0]["code"], "policy_blocked")

    def test_task_assign_rejects_lock_conflict(self) -> None:
        self.init_repo()
        self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-lock-owner",
            lease_id="lease-contract-lock-owner",
            worker_id="worker-lock-owner",
        )
        self.seed_worker(worker_id="worker-lock-target")
        task_id = self.seed_task(
            task_id="task-contract-lock-target",
            protected_surfaces=["docs/contract-close.md"],
        )

        result = self.run_cli("task", "assign", "--task", task_id, "--worker", "worker-lock-target", "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task assign")
        self.assertEqual(payload["errors"][0]["code"], "conflict")

    def test_task_close_completes_active_task_and_releases_live_ownership(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock()
        self.create_checkpointable_repo_changes()
        checkpoint_payload = self.capture_task_checkpoint(task_id, "task.close")
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]

        result = self.run_cli(
            "task",
            "close",
            "--task",
            task_id,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task close")
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "completed")
        self.assertIsNone(payload["data"]["result"]["task"]["current_worker_id"])
        self.assertIsNone(payload["data"]["result"]["task"]["current_lease_id"])
        self.assertEqual(payload["data"]["result"]["lease"]["lease_id"], lease_id)
        self.assertEqual(payload["data"]["result"]["lease"]["state"], "completed")
        self.assertEqual(payload["data"]["result"]["locks"][0]["state"], "released")
        self.assertEqual(payload["data"]["result"]["checkpoint_id"], checkpoint_id)
        self.assertTrue(payload["data"]["result"]["controller_state_changed"])
        self.assertEqual(payload["data"]["result"]["review_gate"]["status"], "satisfied")
        decision_event_id = payload["data"]["result"]["decision_event_id"]
        self.assertEqual(payload["data"]["event"]["event_type"], "task.completed")
        self.assertEqual(payload["data"]["event"]["payload"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(payload["data"]["event"]["payload"]["decision_event_id"], decision_event_id)
        event_id = payload["data"]["event"]["event_id"]

        lease_history_payload = json.loads(self.run_cli("lease", "history", "--task", task_id, "--json").stdout)
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "completed")

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "released")

        event_payload = json.loads(self.run_cli("event", "inspect", "--event", event_id, "--json").stdout)
        self.assertEqual(event_payload["data"]["event"]["event_type"], "task.completed")
        self.assertEqual(event_payload["data"]["checkpoint"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(event_payload["data"]["decision_event"]["event_id"], decision_event_id)
        self.assertEqual(event_payload["data"]["decision_event"]["actor_id"], "operator.checkpoint@example.test")

        overview_payload = json.loads(self.run_cli("overview", "show", "--json").stdout)
        self.assertEqual(overview_payload["data"]["overview"]["task_summary"]["completed"], 1)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], decision_event_id)

    def test_task_close_rejects_non_active_state_with_contract_conflict(self) -> None:
        self.init_repo()
        task_id = self.seed_task(task_id="task-contract-close-conflict")

        result = self.run_cli("task", "close", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task close")
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertIsNone(payload["data"]["event"])

    def test_task_close_blocks_without_checkpoint_and_leaves_state_unchanged(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-close-missing-checkpoint",
            lease_id="lease-close-missing-checkpoint",
            worker_id="worker-close-missing-checkpoint",
        )

        result = self.run_cli("task", "close", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("no current task.close checkpoint is recorded", payload["errors"][0]["message"])
        self.assertFalse(payload["data"]["result"]["controller_state_changed"])
        self.assertEqual(payload["data"]["result"]["review_gate"]["gate_outcome"], "missing")
        self.assertEqual(
            payload["data"]["result"]["next_action"],
            f"macs task checkpoint --task {task_id} --target-action task.close",
        )

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "active")
        self.assertEqual(inspect_payload["task"]["current_lease_id"], lease_id)

        lease_payload = json.loads(self.run_cli("lease", "inspect", "--lease", lease_id, "--json").stdout)
        self.assertEqual(lease_payload["data"]["lease"]["state"], "active")

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "active")

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            checkpoint_count = conn.execute("SELECT COUNT(*) FROM review_checkpoints").fetchone()[0]
            decision_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'intervention.decision_recorded'"
            ).fetchone()[0]
            completed_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type IN ('lease.completed', 'task.completed')"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(checkpoint_count, 0)
        self.assertEqual(decision_count, 0)
        self.assertEqual(completed_count, 0)

    def test_task_close_blocks_with_stale_checkpoint_after_repo_changes(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-close-stale-checkpoint",
            lease_id="lease-close-stale-checkpoint",
            worker_id="worker-close-stale-checkpoint",
        )
        self.create_checkpointable_repo_changes()
        checkpoint_payload = self.capture_task_checkpoint(task_id, "task.close")
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]
        self.create_checkpointable_repo_changes()

        result = self.run_cli("task", "close", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["review_gate"]["gate_outcome"], "stale")
        self.assertEqual(payload["data"]["result"]["review_gate"]["reason"], "repo_state_mismatch")
        self.assertEqual(payload["data"]["result"]["review_gate"]["checkpoint"]["checkpoint_id"], checkpoint_id)

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "active")
        self.assertEqual(inspect_payload["task"]["current_lease_id"], lease_id)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            checkpoint_row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
            decision_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'intervention.decision_recorded'"
            ).fetchone()[0]
            completed_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type IN ('lease.completed', 'task.completed')"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertIsNone(checkpoint_row[0])
        self.assertEqual(decision_count, 0)
        self.assertEqual(completed_count, 0)

    def test_task_close_blocks_when_only_archive_checkpoint_exists(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-close-mismatched-checkpoint",
            lease_id="lease-close-mismatched-checkpoint",
            worker_id="worker-close-mismatched-checkpoint",
        )
        self.create_checkpointable_repo_changes()
        checkpoint_payload = self.capture_task_checkpoint(task_id, "task.archive")
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]

        result = self.run_cli("task", "close", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["review_gate"]["gate_outcome"], "mismatched")
        self.assertEqual(
            payload["data"]["result"]["review_gate"]["conflicting_checkpoint"]["checkpoint_id"],
            checkpoint_id,
        )
        self.assertEqual(
            payload["data"]["result"]["review_gate"]["conflicting_checkpoint"]["target_action"],
            "task.archive",
        )

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "active")
        self.assertEqual(inspect_payload["task"]["current_lease_id"], lease_id)

    def test_task_close_uses_true_latest_checkpoint_when_same_second_records_exist(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-close-same-second-checkpoints",
            lease_id="lease-close-same-second-checkpoints",
            worker_id="worker-close-same-second-checkpoints",
        )
        self.create_checkpointable_repo_changes()
        older_checkpoint_id, newer_checkpoint_id = self.seed_same_second_checkpoints(
            task_id=task_id,
            target_action="task.close",
            affected_refs={
                "task_id": task_id,
                "lease_id": lease_id,
                "worker_id": "worker-close-same-second-checkpoints",
            },
        )

        result = self.run_cli(
            "task",
            "close",
            "--task",
            task_id,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.close.same-second@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["checkpoint_id"], newer_checkpoint_id)
        self.assertEqual(payload["data"]["result"]["review_gate"]["checkpoint"]["checkpoint_id"], newer_checkpoint_id)
        decision_event_id = payload["data"]["result"]["decision_event_id"]

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            older_row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (older_checkpoint_id,),
            ).fetchone()
            newer_row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (newer_checkpoint_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNone(older_row[0])
        self.assertEqual(newer_row[0], decision_event_id)

    def test_task_checkpoint_help_is_discoverable_under_task_family(self) -> None:
        result = self.run_cli("task", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("checkpoint", result.stdout)

        checkpoint_help = self.run_cli("task", "checkpoint", "--help")
        self.assertEqual(checkpoint_help.returncode, 0, checkpoint_help.stderr)
        self.assertIn("--target-action", checkpoint_help.stdout)
        self.assertIn("task.close", checkpoint_help.stdout)

    def test_task_checkpoint_captures_repo_native_evidence_and_returns_contract_envelope(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id, lease_id = self.seed_active_task_with_lease_and_lock(
            task_id="task-contract-checkpoint",
            lease_id="lease-contract-checkpoint",
            worker_id="worker-codex-checkpoint",
        )
        self.create_checkpointable_repo_changes()

        result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.close",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(set(payload.keys()), {"ok", "command", "timestamp", "warnings", "errors", "data"})
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task checkpoint")
        self.assertEqual(payload["errors"], [])

        action = payload["data"]["result"]
        self.assertEqual(action["task"]["task_id"], task_id)
        self.assertEqual(action["task"]["state"], "active")
        self.assertEqual(action["task_id"], task_id)
        self.assertEqual(action["target_action"], "task.close")
        self.assertEqual(action["affected_refs"]["task_id"], task_id)
        self.assertEqual(action["affected_refs"]["lease_id"], lease_id)
        self.assertEqual(action["affected_refs"]["worker_id"], "worker-codex-checkpoint")
        self.assertTrue(action["controller_state_changed"])
        self.assertEqual(action["next_action"], f"macs task inspect --task {task_id}")

        checkpoint_id = action["checkpoint_id"]
        artifact_refs = action["artifact_refs"]
        bundle_dir = self.repo_root / artifact_refs["bundle_dir"]
        self.assertTrue(bundle_dir.is_dir())
        for key in (
            "metadata_json",
            "head_ref",
            "git_status",
            "git_untracked",
            "git_diff",
            "git_diff_stat",
            "git_diff_cached",
            "git_diff_cached_stat",
        ):
            self.assertTrue((self.repo_root / artifact_refs[key]).exists(), key)

        event = payload["data"]["event"]
        self.assertEqual(event["event_type"], "review.checkpoint_recorded")
        self.assertEqual(event["actor_type"], "operator")
        self.assertEqual(event["actor_id"], "operator.checkpoint@example.test")
        self.assertEqual(event["payload"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(event["payload"]["target_action"], "task.close")

        inspect_event_payload = json.loads(
            self.run_cli("event", "inspect", "--event", event["event_id"], "--json").stdout
        )
        self.assertEqual(inspect_event_payload["data"]["checkpoint"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(inspect_event_payload["data"]["checkpoint"]["target_action"], "task.close")

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            row = conn.execute(
                """
                SELECT task_id, target_action, actor_id, event_id
                FROM review_checkpoints
                WHERE checkpoint_id = ?
                """,
                (checkpoint_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], task_id)
        self.assertEqual(row[1], "task.close")
        self.assertEqual(row[2], "operator.checkpoint@example.test")
        self.assertEqual(row[3], event["event_id"])

    def test_task_checkpoint_rejects_non_git_repo_without_persisting_authority(self) -> None:
        self.init_repo()
        task_id = self.seed_task(task_id="task-contract-checkpoint-fail", summary="Checkpoint fail-closed")

        result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.close",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task checkpoint")
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")
        self.assertFalse(payload["data"]["result"]["controller_state_changed"])

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            checkpoint_count = conn.execute("SELECT COUNT(*) FROM review_checkpoints").fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'review.checkpoint_recorded'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(checkpoint_count, 0)
        self.assertEqual(event_count, 0)

    def test_task_checkpoint_rejects_unsupported_or_unknown_target_actions_without_persisting_authority(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_task(task_id="task-checkpoint-invalid-target", summary="Checkpoint invalid target")
        self.create_checkpointable_repo_changes()

        for target_action in ("task.assign", "made.up.action"):
            with self.subTest(target_action=target_action):
                result = self.run_cli(
                    "task",
                    "checkpoint",
                    "--task",
                    task_id,
                    "--target-action",
                    target_action,
                    "--json",
                    env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
                )
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["errors"][0]["code"], "invalid_argument")
                self.assertIn("supported values are 'task.close' and 'task.archive'", payload["errors"][0]["message"])
                self.assertFalse(payload["data"]["result"]["controller_state_changed"])

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            checkpoint_count = conn.execute("SELECT COUNT(*) FROM review_checkpoints").fetchone()[0]
            event_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'review.checkpoint_recorded'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(checkpoint_count, 0)
        self.assertEqual(event_count, 0)

    def test_task_checkpoint_captures_reviewable_untracked_file_diff_when_repo_has_only_new_files(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_task(task_id="task-untracked-only-checkpoint", summary="Checkpoint untracked-only evidence")
        self.create_untracked_only_repo_changes()

        result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.close",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        artifact_refs = payload["data"]["result"]["artifact_refs"]
        git_diff_path = self.repo_root / artifact_refs["git_diff"]
        git_diff_stat_path = self.repo_root / artifact_refs["git_diff_stat"]
        git_diff_summary_path = self.repo_root / artifact_refs["git_diff_summary"]

        git_diff_output = git_diff_path.read_text(encoding="utf-8")
        self.assertIn("docs/untracked-only-checkpoint.md", git_diff_output)
        self.assertIn("+untracked only checkpoint evidence", git_diff_output)
        self.assertIn("docs/untracked-only-checkpoint.md", git_diff_stat_path.read_text(encoding="utf-8"))
        self.assertIn("create mode", git_diff_summary_path.read_text(encoding="utf-8"))

    def test_task_archive_marks_terminal_task_archived(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_completed_task()
        self.create_checkpointable_repo_changes()
        checkpoint_payload = self.capture_task_checkpoint(task_id, "task.archive")
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]

        result = self.run_cli(
            "task",
            "archive",
            "--task",
            task_id,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task archive")
        self.assertEqual(payload["data"]["result"]["task"]["task_id"], task_id)
        self.assertEqual(payload["data"]["result"]["task"]["state"], "archived")
        self.assertEqual(payload["data"]["result"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(payload["data"]["result"]["review_gate"]["status"], "satisfied")
        decision_event_id = payload["data"]["result"]["decision_event_id"]
        self.assertEqual(payload["data"]["event"]["event_type"], "task.archived")
        self.assertEqual(payload["data"]["event"]["payload"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(payload["data"]["event"]["payload"]["decision_event_id"], decision_event_id)
        event_id = payload["data"]["event"]["event_id"]

        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "archived")

        event_payload = json.loads(self.run_cli("event", "inspect", "--event", event_id, "--json").stdout)
        self.assertEqual(event_payload["data"]["event"]["event_type"], "task.archived")
        self.assertEqual(event_payload["data"]["checkpoint"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(event_payload["data"]["decision_event"]["event_id"], decision_event_id)

        overview_payload = json.loads(self.run_cli("overview", "show", "--json").stdout)
        self.assertEqual(overview_payload["data"]["overview"]["task_summary"]["archived"], 1)

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], decision_event_id)

    def test_task_archive_blocks_without_checkpoint_and_leaves_state_unchanged(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_completed_task(task_id="task-archive-missing-checkpoint")

        result = self.run_cli("task", "archive", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertIn("no current task.archive checkpoint is recorded", payload["errors"][0]["message"])
        self.assertFalse(payload["data"]["result"]["controller_state_changed"])
        self.assertEqual(payload["data"]["result"]["review_gate"]["gate_outcome"], "missing")
        self.assertEqual(
            payload["data"]["result"]["next_action"],
            f"macs task checkpoint --task {task_id} --target-action task.archive",
        )

        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "completed")

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            checkpoint_count = conn.execute("SELECT COUNT(*) FROM review_checkpoints").fetchone()[0]
            archived_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'task.archived'"
            ).fetchone()[0]
            decision_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_type = 'intervention.decision_recorded'"
            ).fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(checkpoint_count, 0)
        self.assertEqual(archived_count, 0)
        self.assertEqual(decision_count, 0)

    def test_task_archive_blocks_when_only_close_checkpoint_exists(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_completed_task(task_id="task-archive-mismatched-checkpoint")
        self.create_checkpointable_repo_changes()
        checkpoint_payload = self.capture_task_checkpoint(task_id, "task.close")
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]

        result = self.run_cli("task", "archive", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["errors"][0]["code"], "policy_blocked")
        self.assertEqual(payload["data"]["result"]["review_gate"]["gate_outcome"], "mismatched")
        self.assertEqual(
            payload["data"]["result"]["review_gate"]["conflicting_checkpoint"]["checkpoint_id"],
            checkpoint_id,
        )
        self.assertEqual(
            payload["data"]["result"]["review_gate"]["conflicting_checkpoint"]["target_action"],
            "task.close",
        )

        inspect_task_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_task_payload["task"]["state"], "completed")

    def test_task_archive_uses_true_latest_checkpoint_when_same_second_records_exist(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_completed_task(task_id="task-archive-same-second-checkpoints")
        self.create_checkpointable_repo_changes()
        older_checkpoint_id, newer_checkpoint_id = self.seed_same_second_checkpoints(
            task_id=task_id,
            target_action="task.archive",
            affected_refs={"task_id": task_id},
        )

        result = self.run_cli(
            "task",
            "archive",
            "--task",
            task_id,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.archive.same-second@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["result"]["checkpoint_id"], newer_checkpoint_id)
        self.assertEqual(payload["data"]["result"]["review_gate"]["checkpoint"]["checkpoint_id"], newer_checkpoint_id)
        decision_event_id = payload["data"]["result"]["decision_event_id"]

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            older_row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (older_checkpoint_id,),
            ).fetchone()
            newer_row = conn.execute(
                "SELECT decision_event_id FROM review_checkpoints WHERE checkpoint_id = ?",
                (newer_checkpoint_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNone(older_row[0])
        self.assertEqual(newer_row[0], decision_event_id)

    def test_task_action_human_readable_output_reports_final_state(self) -> None:
        self.init_repo()
        self.init_git_repo()

        create_result = self.run_cli("task", "create", "--summary", "Human output create")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        self.assertIn("Workflow Class: implementation", create_result.stdout)

        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker()
        self.seed_worker_with_tmux(
            worker_id="worker-human-assign",
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )
        assign_task_id = self.seed_task(task_id="task-human-assign")
        assign_result = self.run_cli("task", "assign", "--task", assign_task_id, "--worker", "worker-human-assign")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        self.assertIn(f"Task: {assign_task_id}", assign_result.stdout)
        self.assertIn("State: active", assign_result.stdout)

        close_task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-human-close",
            lease_id="lease-human-close",
            worker_id="worker-human-close",
        )
        self.create_checkpointable_repo_changes()
        self.capture_task_checkpoint(close_task_id, "task.close")
        close_result = self.run_cli("task", "close", "--task", close_task_id)
        self.assertEqual(close_result.returncode, 0, close_result.stderr)
        self.assertIn("State: completed", close_result.stdout)
        self.assertIn("Locks Released: 1", close_result.stdout)
        self.assertIn("Checkpoint: checkpoint-", close_result.stdout)
        self.assertIn("Decision Event: evt-intervention-decision-", close_result.stdout)

        archive_task_id = self.seed_completed_task(task_id="task-human-archive")
        self.create_checkpointable_repo_changes()
        self.capture_task_checkpoint(archive_task_id, "task.archive")
        archive_result = self.run_cli("task", "archive", "--task", archive_task_id)
        self.assertEqual(archive_result.returncode, 0, archive_result.stderr)
        self.assertIn("State: archived", archive_result.stdout)
        self.assertIn("Checkpoint: checkpoint-", archive_result.stdout)
        self.assertIn("Decision Event: evt-intervention-decision-", archive_result.stdout)

    def test_task_checkpoint_human_readable_reports_checkpoint_metadata_and_next_action(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_task(task_id="task-human-checkpoint", summary="Human checkpoint slice")
        self.create_checkpointable_repo_changes()

        result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "archive",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Task: {task_id}", result.stdout)
        self.assertIn("Checkpoint: checkpoint-", result.stdout)
        self.assertIn("Target Action: task.archive", result.stdout)
        self.assertIn("Event ID: evt-review-checkpoint-", result.stdout)
        self.assertIn("Controller State Changed: yes", result.stdout)
        self.assertIn("Evidence Refs: bundle_dir=.codex/orchestration/checkpoints/", result.stdout)
        self.assertIn(f"Next Action: macs task inspect --task {task_id}", result.stdout)

    def test_task_pause_human_readable_stacks_key_fields_on_narrow_no_color_terminals(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-human-pause",
            lease_id="lease-human-pause",
            worker_id="worker-human-pause",
        )

        result = self.run_cli(
            "task",
            "pause",
            "--task",
            task_id,
            "--confirm",
            env_overrides={"COLUMNS": "80", "NO_COLOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotRegex(result.stdout, r"\x1b\[[0-9;]*m")
        self.assertIn(f"Task:\n  {task_id}", result.stdout)
        self.assertIn("Lease:\n  lease-human-pause (paused)", result.stdout)
        self.assertIn("Runtime Pause Depth:\n  controller_only", result.stdout)

    def test_task_pause_human_readable_reports_event_state_change_and_next_action(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-human-pause-summary",
            lease_id="lease-human-pause-summary",
            worker_id="worker-human-pause-summary",
        )

        result = self.run_cli("task", "pause", "--task", task_id, "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Decision Rights: operator_confirmed", result.stdout)
        self.assertIn("Confirmation: confirmed", result.stdout)
        self.assertIn("Controller State Changed: yes", result.stdout)
        self.assertIn("Event ID: evt-task-pause-", result.stdout)
        self.assertIn(f"Next Action: macs task inspect --task {task_id}", result.stdout)

    def test_task_pause_human_readable_missing_confirmation_reports_guardrail(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-human-pause-confirm-required",
            lease_id="lease-human-pause-confirm-required",
            worker_id="worker-human-pause-confirm-required",
        )

        result = self.run_cli("task", "pause", "--task", task_id)
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertIn("requires explicit operator confirmation", result.stderr)
        self.assertIn("Decision Rights: operator_confirmed", result.stderr)
        self.assertIn("Controller State Changed: no", result.stderr)
        self.assertIn(f"Affected Refs: task={task_id}", result.stderr)

    def test_task_resume_human_readable_reports_event_state_change_and_next_action(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_active_task_with_lease_and_lock(
            task_id="task-human-resume-summary",
            lease_id="lease-human-resume-summary",
            worker_id="worker-human-resume-summary",
        )
        pause_result = self.run_cli("task", "pause", "--task", task_id, "--confirm", "--json")
        self.assertEqual(pause_result.returncode, 0, pause_result.stdout + pause_result.stderr)

        result = self.run_cli("task", "resume", "--task", task_id, "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Decision Rights: operator_confirmed", result.stdout)
        self.assertIn("Confirmation: confirmed", result.stdout)
        self.assertIn("Controller State Changed: yes", result.stdout)
        self.assertIn("Event ID: evt-task-resume-", result.stdout)
        self.assertIn(f"Next Action: macs task inspect --task {task_id}", result.stdout)

    def test_task_archive_rejects_non_terminal_state_with_contract_conflict(self) -> None:
        self.init_repo()
        task_id = self.seed_task(task_id="task-contract-archive-conflict")

        result = self.run_cli("task", "archive", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task archive")
        self.assertEqual(payload["errors"][0]["code"], "conflict")
        self.assertIsNone(payload["data"]["event"])

    def test_task_assign_side_effect_failure_reverts_to_safe_state(self) -> None:
        self.init_repo()
        self.seed_worker()
        task_id = self.seed_task(task_id="task-contract-assign-failure", protected_surfaces=["docs/assign-failure.md"])

        result = self.run_cli("task", "assign", "--task", task_id, "--worker", "worker-codex-contract", "--json")
        self.assertEqual(result.returncode, 6, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs task assign")
        self.assertEqual(payload["errors"][0]["code"], "side_effect_failed")

        inspect_task_payload = json.loads(
            self.run_cli("task", "inspect", "--task", task_id, "--json").stdout
        )
        self.assertEqual(inspect_task_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_task_payload["task"]["current_worker_id"])
        self.assertIsNone(inspect_task_payload["task"]["current_lease_id"])

        lease_history_payload = json.loads(
            self.run_cli("lease", "history", "--task", task_id, "--json").stdout
        )
        self.assertEqual(lease_history_payload["data"]["leases"][0]["state"], "revoked")

        lock_payload = json.loads(self.run_cli("lock", "list", "--json").stdout)
        self.assertEqual(lock_payload["data"]["locks"][0]["state"], "released")


if __name__ == "__main__":
    unittest.main()
