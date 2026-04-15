#!/usr/bin/env python3
"""Black-box CLI regressions for inspect-context surfaces."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = [sys.executable, "-m", "tools.orchestration.cli.main"]


class InspectContextCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-inspect-cli-test-"))
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
        self.assertEqual(self.run_git("config", "user.email", "inspect@example.test").returncode, 0)
        self.assertEqual(self.run_git("config", "user.name", "Inspect Test").returncode, 0)
        (self.repo_root / ".gitignore").write_text(".codex/\n", encoding="utf-8")
        (self.repo_root / "README.md").write_text("baseline\n", encoding="utf-8")
        add_result = self.run_git("add", ".gitignore", "README.md")
        self.assertEqual(add_result.returncode, 0, add_result.stdout + add_result.stderr)
        commit_result = self.run_git("commit", "-m", "Initial commit")
        self.assertEqual(commit_result.returncode, 0, commit_result.stdout + commit_result.stderr)

    def create_checkpointable_repo_changes(self) -> None:
        readme_path = self.repo_root / "README.md"
        readme_path.write_text(readme_path.read_text(encoding="utf-8") + "inspect checkpoint change\n", encoding="utf-8")
        docs_dir = self.repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "inspect-checkpoint.md").write_text("inspect checkpoint context\n", encoding="utf-8")

    def seed_completed_task(self) -> str:
        create_result = self.run_cli("task", "create", "--summary", "Inspect archived task context", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            conn.execute("UPDATE tasks SET state = 'completed' WHERE task_id = ?", (task_id,))
            conn.commit()
        finally:
            conn.close()
        return task_id

    def seed_worker_row(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        adapter_id: str,
        capabilities: list[str],
        operator_tags: list[str] | None = None,
        state: str = "ready",
        tmux_socket: str = "/tmp/macs-inspect.sock",
        tmux_session: str = "macs-inspect",
        tmux_pane: str = "%1",
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
                    json.dumps(capabilities),
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    json.dumps(operator_tags or ["registered"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id

    def read_target_pane(self) -> str:
        return (self.repo_root / ".codex" / "target-pane.txt").read_text(encoding="utf-8").strip()

    def update_governance_policy(self, mutator) -> dict[str, object]:
        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        updated = mutator(governance_policy)
        governance_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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

    def write_worker_env(self, values: dict[str, str]) -> Path:
        env_path = self.repo_root / ".codex" / "tmux-worker.env"
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(
            "\n".join(f"{key}={json.dumps(value)}" for key, value in sorted(values.items())) + "\n",
            encoding="utf-8",
        )
        return env_path

    def create_tmux_session(self, socket: Path, session: str, *, window_name: str) -> str:
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", window_name],
            check=True,
            capture_output=True,
            text=True,
        )
        pane_result = subprocess.run(
            ["tmux", "-S", str(socket), "list-panes", "-t", session, "-F", "#{pane_id}"],
            check=True,
            capture_output=True,
            text=True,
        )
        pane_id = pane_result.stdout.strip().splitlines()[0]
        self.assertTrue(pane_id)
        return pane_id

    def stage_tmux_capture(self, socket: Path, pane_id: str, content: str) -> None:
        if not content:
            return
        subprocess.run(
            ["tmux", "-S", str(socket), "send-keys", "-t", pane_id, "-l", content],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_cli_in_tmux(self, socket: Path, session: str, *args: str) -> subprocess.CompletedProcess[str]:
        stdout_path = self.temp_dir / f"{session}-stdout.txt"
        stderr_path = self.temp_dir / f"{session}-stderr.txt"
        exit_path = self.temp_dir / f"{session}-exit.txt"
        shell_command = (
            f"cd {shlex.quote(str(REPO_ROOT))} && "
            f"export PYTHONPATH={shlex.quote(self.env['PYTHONPATH'])} && "
            f"{shlex.quote(sys.executable)} -m tools.orchestration.cli.main "
            f"--repo {shlex.quote(str(self.repo_root))} "
            f"{' '.join(shlex.quote(arg) for arg in args)} "
            f"> {shlex.quote(str(stdout_path))} 2> {shlex.quote(str(stderr_path))}; "
            f"printf '%s' \"$?\" > {shlex.quote(str(exit_path))}"
        )
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "bash", "-lc", shell_command],
            check=True,
            capture_output=True,
            text=True,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            if exit_path.exists():
                break
            time.sleep(0.05)
        self.assertTrue(exit_path.exists(), f"tmux command did not finish: {shell_command}")
        return subprocess.CompletedProcess(
            args=CLI + ["--repo", str(self.repo_root), *args],
            returncode=int(exit_path.read_text(encoding="utf-8").strip() or "1"),
            stdout=stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else "",
            stderr=stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else "",
        )

    def assign_secret_backed_task(self) -> tuple[str, str, str]:
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
                }
            ]
        )

        socket = self.temp_dir / "secret-inspect.sock"
        session = f"secret-inspect-{os.getpid()}"
        pane_id = self.create_tmux_session(socket, session, window_name="codex")
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.seed_worker_row(
            worker_id="worker-codex-secret-inspect",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=str(socket),
            tmux_session=session,
            tmux_pane=pane_id,
        )

        create_result = self.run_cli("task", "create", "--summary", "Secret inspect slice", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stdout + assign_result.stderr)
        event_id = json.loads(assign_result.stdout)["data"]["event"]["event_id"]
        return task_id, event_id, runtime_secret

    def seed_governed_task_context(self, *, close_task: bool = False) -> dict[str, str]:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        self.init_git_repo()
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
                }
            ]
        )
        self.configure_surface_version_pin(
            adapter_id="codex",
            expected_runtime_identity="codex",
            expected_model_identity="gpt-5.4",
        )

        socket = self.temp_dir / "governed-inspect.sock"
        session = f"governed-inspect-{os.getpid()}"
        pane_id = self.create_tmux_session(socket, session, window_name="codex")
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.stage_tmux_capture(socket, pane_id, "codex --model gpt-5.4 --sandbox workspace-write --yolo")
        self.seed_worker_row(
            worker_id="worker-codex-governed-inspect",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=str(socket),
            tmux_session=session,
            tmux_pane=pane_id,
        )

        create_result = self.run_cli("task", "create", "--summary", "Governed inspect slice", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stdout + assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)

        self.create_checkpointable_repo_changes()
        checkpoint_result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.close",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.governance@example.test"},
        )
        self.assertEqual(checkpoint_result.returncode, 0, checkpoint_result.stdout + checkpoint_result.stderr)
        checkpoint_payload = json.loads(checkpoint_result.stdout)

        scenario = {
            "task_id": task_id,
            "assign_event_id": assign_payload["data"]["event"]["event_id"],
            "checkpoint_event_id": checkpoint_payload["data"]["event"]["event_id"],
            "checkpoint_id": checkpoint_payload["data"]["result"]["checkpoint_id"],
            "runtime_secret": runtime_secret,
        }

        if close_task:
            close_result = self.run_cli(
                "task",
                "close",
                "--task",
                task_id,
                "--json",
                env_overrides={"MACS_OPERATOR_ID": "operator.governance@example.test"},
            )
            self.assertEqual(close_result.returncode, 0, close_result.stdout + close_result.stderr)
            close_payload = json.loads(close_result.stdout)
            scenario["close_event_id"] = close_payload["data"]["event"]["event_id"]
            scenario["decision_event_id"] = close_payload["data"]["result"]["decision_event_id"]
        return scenario

    def seed_degraded_worker_context(
        self,
        *,
        tmux_socket: str = "/tmp/macs-inspect.sock",
        tmux_session: str = "macs-test",
        tmux_pane: str = "%7",
    ) -> tuple[str, str, str]:
        worker_id = "worker-local-degraded"
        task_id = "task-inspect-degraded"
        lease_id = "lease-inspect-degraded"
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
                    "local",
                    "local",
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
                    "degraded",
                    json.dumps(["analysis", "documentation"]),
                    "required_only",
                    self.iso_now(seconds_ago=120),
                    self.iso_now(seconds_ago=120),
                    "interruptible",
                    json.dumps(["registered"]),
                ),
            )
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, workflow_class, intent,
                    required_capabilities, protected_surfaces, priority, state,
                    current_worker_id, current_lease_id, routing_policy_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "Inspect degraded worker evidence",
                    "Inspect degraded worker evidence",
                    "analysis",
                    "Inspect degraded worker evidence",
                    json.dumps(["analysis"]),
                    json.dumps(["docs/getting-started.md"]),
                    "high",
                    "active",
                    worker_id,
                    lease_id,
                    "policy-v1",
                ),
            )
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, task_id, worker_id, state, issued_at, accepted_at,
                    ended_at, replacement_lease_id, intervention_reason, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    task_id,
                    worker_id,
                    "active",
                    self.iso_now(seconds_ago=115),
                    self.iso_now(seconds_ago=114),
                    None,
                    None,
                    None,
                    "decision-inspect-001",
                ),
            )
            conn.execute(
                """
                INSERT INTO routing_decisions (
                    decision_id, task_id, selected_worker_id, rationale, evidence_ref, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "decision-inspect-001",
                    task_id,
                    worker_id,
                    json.dumps(
                        {
                            "summary": "Selected degraded worker only to preserve current ownership during intervention triage."
                        },
                        sort_keys=True,
                    ),
                    json.dumps({"probe": "evidence-inspect-001"}, sort_keys=True),
                    self.iso_now(seconds_ago=116),
                ),
            )
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-inspect-001",
                    "surface",
                    "docs/getting-started.md",
                    "exclusive",
                    "held",
                    task_id,
                    lease_id,
                    "policy-v1",
                    self.iso_now(seconds_ago=111),
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-worker-health-001",
                    "worker.health_reclassified",
                    "worker",
                    worker_id,
                    self.iso_now(seconds_ago=113),
                    "controller",
                    "controller-main",
                    "corr-worker-health-001",
                    None,
                    json.dumps({"previous_state": "ready", "next_state": "degraded"}, sort_keys=True),
                    "none",
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-task-activated-001",
                    "task.activated",
                    "task",
                    task_id,
                    self.iso_now(seconds_ago=112),
                    "controller",
                    "controller-main",
                    "corr-task-activated-001",
                    None,
                    json.dumps({"task_id": task_id, "lease_id": lease_id, "worker_id": worker_id}, sort_keys=True),
                    "none",
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id, task_id, lease_id

    def seed_paused_task_context(
        self,
        *,
        tmux_socket: str = "/tmp/macs-paused.sock",
        tmux_session: str = "macs-paused",
        tmux_pane: str = "%9",
    ) -> tuple[str, str, str]:
        worker_id = "worker-local-paused"
        task_id = "task-inspect-paused"
        lease_id = "lease-inspect-paused"
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
                    "local",
                    "local",
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
                    "ready",
                    json.dumps(["analysis", "documentation"]),
                    "required_only",
                    self.iso_now(seconds_ago=20),
                    self.iso_now(seconds_ago=20),
                    "interruptible",
                    json.dumps(["registered"]),
                ),
            )
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, workflow_class, intent,
                    required_capabilities, protected_surfaces, priority, state,
                    current_worker_id, current_lease_id, routing_policy_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "Inspect paused task context",
                    "Inspect paused task context",
                    "analysis",
                    "Inspect paused task context",
                    json.dumps(["analysis"]),
                    json.dumps(["docs/getting-started.md"]),
                    "high",
                    "intervention_hold",
                    worker_id,
                    lease_id,
                    "policy-pause-v1",
                ),
            )
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, task_id, worker_id, state, issued_at, accepted_at,
                    ended_at, replacement_lease_id, intervention_reason, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    task_id,
                    worker_id,
                    "paused",
                    self.iso_now(seconds_ago=35),
                    self.iso_now(seconds_ago=34),
                    None,
                    None,
                    "operator_pause",
                    "decision-pause-001",
                ),
            )
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-paused-001",
                    "surface",
                    "docs/getting-started.md",
                    "exclusive",
                    "held",
                    task_id,
                    lease_id,
                    "policy-pause-v1",
                    self.iso_now(seconds_ago=33),
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-intervention-decision-pause-001",
                    "intervention.decision_recorded",
                    "task",
                    task_id,
                    self.iso_now(seconds_ago=33),
                    "operator",
                    "operator.pause@example.test",
                    "corr-task-paused-001",
                    None,
                    json.dumps(
                        {
                            "decision_action": "pause",
                            "decision_class": "operator_confirmed",
                            "intervention_rationale": "operator requested a safe in-place pause",
                            "affected_refs": {
                                "task_id": task_id,
                                "lease_id": lease_id,
                                "worker_id": worker_id,
                                "recovery_run_id": None,
                            },
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-task-paused-001",
                    "task.paused",
                    "task",
                    task_id,
                    self.iso_now(seconds_ago=32),
                    "controller",
                    "controller-main",
                    "corr-task-paused-001",
                    "evt-lease-paused-001",
                    json.dumps(
                        {
                            "task_id": task_id,
                            "lease_id": lease_id,
                            "worker_id": worker_id,
                            "decision_event_id": "evt-intervention-decision-pause-001",
                            "intervention_rationale": "operator requested a safe in-place pause",
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-lease-paused-001",
                    "lease.paused",
                    "lease",
                    lease_id,
                    self.iso_now(seconds_ago=32),
                    "controller",
                    "controller-main",
                    "corr-task-paused-001",
                    "evt-intervention-decision-pause-001",
                    json.dumps(
                        {
                            "task_id": task_id,
                            "lease_id": lease_id,
                            "worker_id": worker_id,
                            "intervention_reason": "operator_pause",
                            "decision_event_id": "evt-intervention-decision-pause-001",
                            "intervention_rationale": "operator requested a safe in-place pause",
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id, task_id, lease_id

    def seed_suspended_task_context(
        self,
        *,
        tmux_socket: str = "/tmp/macs-suspended.sock",
        tmux_session: str = "macs-suspended",
        tmux_pane: str = "%10",
    ) -> tuple[str, str, str]:
        worker_id = "worker-local-suspended"
        task_id = "task-inspect-suspended"
        lease_id = "lease-inspect-suspended"
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
                    "local",
                    "local",
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
                    "degraded",
                    json.dumps(["analysis", "documentation"]),
                    "required_only",
                    self.iso_now(seconds_ago=120),
                    self.iso_now(seconds_ago=120),
                    "interruptible",
                    json.dumps(["registered"]),
                ),
            )
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, title, description, workflow_class, intent,
                    required_capabilities, protected_surfaces, priority, state,
                    current_worker_id, current_lease_id, routing_policy_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    "Inspect suspended task context",
                    "Inspect suspended task context",
                    "analysis",
                    "Inspect suspended task context",
                    json.dumps(["analysis"]),
                    json.dumps(["docs/getting-started.md"]),
                    "high",
                    "intervention_hold",
                    worker_id,
                    lease_id,
                    "policy-suspend-v1",
                ),
            )
            conn.execute(
                """
                INSERT INTO leases (
                    lease_id, task_id, worker_id, state, issued_at, accepted_at,
                    ended_at, replacement_lease_id, intervention_reason, evidence_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lease_id,
                    task_id,
                    worker_id,
                    "suspended",
                    self.iso_now(seconds_ago=35),
                    self.iso_now(seconds_ago=34),
                    None,
                    None,
                    "worker_state_degraded",
                    "decision-suspend-001",
                ),
            )
            conn.execute(
                """
                INSERT INTO locks (
                    lock_id, target_type, target_ref, mode, state, task_id, lease_id, policy_origin, created_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "lock-suspended-001",
                    "surface",
                    "docs/getting-started.md",
                    "exclusive",
                    "held",
                    task_id,
                    lease_id,
                    "policy-suspend-v1",
                    self.iso_now(seconds_ago=33),
                    None,
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-task-risk-hold-001",
                    "task.risk_hold_applied",
                    "task",
                    task_id,
                    self.iso_now(seconds_ago=32),
                    "controller",
                    "controller-main",
                    "corr-task-risk-hold-001",
                    None,
                    json.dumps({"task_id": task_id, "lease_id": lease_id, "worker_id": worker_id}, sort_keys=True),
                    "none",
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-lease-suspended-001",
                    "lease.suspended",
                    "lease",
                    lease_id,
                    self.iso_now(seconds_ago=32),
                    "controller",
                    "controller-main",
                    "corr-task-risk-hold-001",
                    None,
                    json.dumps(
                        {
                            "task_id": task_id,
                            "lease_id": lease_id,
                            "worker_id": worker_id,
                            "intervention_reason": "worker_state_degraded",
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id, task_id, lease_id

    def seed_recovery_run_context(self) -> tuple[str, str, str, str]:
        worker_id, task_id, lease_id = self.seed_suspended_task_context()
        recovery_run_id = "recovery-task-inspect-suspended"
        successor_worker_id = "worker-local-recovery-target"
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
                    successor_worker_id,
                    "local",
                    "local",
                    "/tmp/macs-recovery-target.sock",
                    "macs-recovery-target",
                    "%14",
                    "ready",
                    json.dumps(["analysis", "documentation"]),
                    "required_only",
                    self.iso_now(seconds_ago=3),
                    self.iso_now(seconds_ago=3),
                    "interruptible",
                    json.dumps(["registered"]),
                ),
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
                    "pending_operator_action",
                    self.iso_now(seconds_ago=10),
                    None,
                    json.dumps(
                        {
                            "kind": "ambiguous_ownership",
                            "basis": "worker_state_degraded",
                            "predecessor_worker_id": worker_id,
                            "predecessor_lease_id": lease_id,
                        },
                        sort_keys=True,
                    ),
                    json.dumps(
                        {
                            "allowed_next_actions": [
                                f"macs task reroute --task {task_id} --worker {successor_worker_id}",
                                f"macs task inspect --task {task_id}",
                            ],
                            "proposed_worker_id": successor_worker_id,
                            "proposed_workflow_class": "analysis",
                            "recommended_action": "reroute",
                        },
                        sort_keys=True,
                    ),
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-intervention-decision-recovery-001",
                    "intervention.decision_recorded",
                    "task",
                    task_id,
                    self.iso_now(seconds_ago=9),
                    "operator",
                    "operator.recovery@example.test",
                    "corr-recovery-inspect-001",
                    None,
                    json.dumps(
                        {
                            "decision_action": "reroute",
                            "decision_class": "operator_confirmed",
                            "intervention_rationale": "operator approved a controlled reroute after degraded ownership",
                            "affected_refs": {
                                "task_id": task_id,
                                "lease_id": lease_id,
                                "worker_id": worker_id,
                                "recovery_run_id": recovery_run_id,
                            },
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.execute(
                """
                INSERT INTO events (
                    event_id, event_type, aggregate_type, aggregate_id, timestamp,
                    actor_type, actor_id, correlation_id, causation_id, payload, redaction_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "evt-recovery-reroute-requested-001",
                    "recovery.retry_requested",
                    "recovery",
                    recovery_run_id,
                    self.iso_now(seconds_ago=8),
                    "controller",
                    "controller-main",
                    "corr-recovery-inspect-001",
                    "evt-intervention-decision-recovery-001",
                    json.dumps(
                        {
                            "task_id": task_id,
                            "recovery_run_id": recovery_run_id,
                            "proposed_worker_id": successor_worker_id,
                            "decision_event_id": "evt-intervention-decision-recovery-001",
                            "intervention_rationale": "operator approved a controlled reroute after degraded ownership",
                        },
                        sort_keys=True,
                    ),
                    "none",
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return worker_id, task_id, lease_id, recovery_run_id

    def seed_interrupted_recovery_context(self) -> tuple[str, str]:
        task_id = "task-inspect-interrupted-recovery"
        recovery_run_id = "recovery-task-inspect-interrupted"
        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"

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
                    task_id,
                    "Inspect interrupted recovery",
                    "Inspect interrupted recovery",
                    "implementation",
                    "Inspect interrupted recovery",
                    json.dumps(["implementation"]),
                    json.dumps(["docs/interrupted-recovery.md"]),
                    "high",
                    "reconciliation",
                    None,
                    None,
                    "policy-v1",
                ),
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
                    self.iso_now(seconds_ago=8),
                    None,
                    json.dumps(
                        {
                            "kind": "ambiguous_ownership",
                            "basis": "worker_state_unavailable",
                            "predecessor_worker_id": "worker-inspect-predecessor",
                            "predecessor_lease_id": "lease-inspect-predecessor",
                        },
                        sort_keys=True,
                    ),
                    json.dumps(
                        {
                            "allowed_next_actions": [
                                f"macs recovery retry --task {task_id}",
                                f"macs recovery reconcile --task {task_id}",
                            ],
                            "proposed_worker_id": "worker-inspect-successor",
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

    def test_worker_inspect_json_surfaces_degraded_context_and_frozen_envelope(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_degraded_worker_context()

        result = self.run_cli("worker", "inspect", "--worker", worker_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(
            set(payload.keys()),
            {"ok", "command", "timestamp", "warnings", "errors", "worker"},
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs worker inspect")
        self.assertIsInstance(payload["timestamp"], str)
        self.assertEqual(payload["errors"], [])
        self.assertNotIn("data", payload)
        self.assertNotIn("error", payload)
        self.assertTrue(any("degraded" in warning.lower() for warning in payload["warnings"]))

        worker = payload["worker"]
        self.assertEqual(worker["worker_id"], worker_id)
        self.assertEqual(worker["runtime_type"], "local")
        self.assertGreaterEqual(worker["freshness_seconds"], 60)

        controller_truth = worker["controller_truth"]
        self.assertEqual(controller_truth["canonical_state"], "degraded")
        self.assertEqual(controller_truth["routability"]["assignable"], False)
        self.assertEqual(controller_truth["routability"]["reason"], "worker_state_degraded")
        self.assertEqual(controller_truth["current_task"]["task_id"], task_id)
        self.assertEqual(controller_truth["current_lease"]["lease_id"], lease_id)
        self.assertEqual(controller_truth["pane_target"]["tmux_session"], "macs-test")
        self.assertEqual(controller_truth["pane_target"]["tmux_pane"], "%7")
        self.assertEqual(controller_truth["recent_event_refs"][0]["event_id"], "evt-worker-health-001")

        adapter_evidence = worker["adapter_evidence"]
        self.assertGreaterEqual(len(adapter_evidence), 1)
        self.assertEqual(adapter_evidence[0]["kind"], "fact")
        self.assertEqual(adapter_evidence[0]["name"], "pane_presence")

    def test_worker_inspect_surfaces_surface_version_mismatch_details_in_json_and_human_output(self) -> None:
        self.init_repo()
        tmux_dir = self.temp_dir / "tmux-inspect-version"
        tmux_dir.mkdir(exist_ok=True)
        socket = tmux_dir / "inspect-version.sock"
        session = f"macs-inspect-version-{os.getpid()}"
        pane_id = self.create_tmux_session(socket, session, window_name="codex-worker")
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.stage_tmux_capture(socket, pane_id, "codex --model gpt-5.4-mini --sandbox workspace-write --yolo")
        self.update_governance_policy(
            lambda policy: {
                **policy,
                "governed_surfaces": {
                    **policy["governed_surfaces"],
                    "allowlisted_surfaces": ["mcp"],
                },
                "surface_version_pins": [
                    {
                        "surface_id": "mcp",
                        "adapter_id": "codex",
                        "workflow_class": "implementation",
                        "operating_profile": "primary_plus_fallback",
                        "expected_runtime_identity": "codex",
                        "expected_model_identity": "gpt-5.4",
                    }
                ],
            }
        )
        self.seed_worker_row(
            worker_id="worker-codex-inspect-version",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=str(socket),
            tmux_session=session,
            tmux_pane=pane_id,
        )

        result = self.run_cli("worker", "inspect", "--worker", "worker-codex-inspect-version", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        blocked = payload["worker"]["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_pin_mismatch")
        self.assertEqual(blocked["selector_context"]["surface_id"], "mcp")
        self.assertEqual(blocked["observed"]["model_identity"]["identity"], "gpt-5.4-mini")

        human_result = self.run_cli("worker", "inspect", "--worker", "worker-codex-inspect-version")
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Surface Version Enforcement:", human_result.stdout)
        self.assertIn("blocked surface_version_pin_mismatch", human_result.stdout)
        self.assertIn("observed=runtime=codex model=gpt-5.4-mini", human_result.stdout)

    def test_task_inspect_json_surfaces_degraded_owner_context_and_frozen_envelope(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_degraded_worker_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(
            set(payload.keys()),
            {"ok", "command", "timestamp", "warnings", "errors", "task"},
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task inspect")
        self.assertIsInstance(payload["timestamp"], str)
        self.assertEqual(payload["errors"], [])
        self.assertNotIn("data", payload)
        self.assertNotIn("error", payload)
        self.assertTrue(any("degraded" in warning.lower() for warning in payload["warnings"]))

        task = payload["task"]
        self.assertEqual(task["task_id"], task_id)
        self.assertEqual(task["state"], "intervention_hold")
        self.assertEqual(
            task["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(task["next_action"], f"reroute or recover task {task_id} before resume")

        controller_truth = task["controller_truth"]
        self.assertEqual(controller_truth["canonical_state"], "intervention_hold")
        self.assertEqual(controller_truth["current_owner"]["worker_id"], worker_id)
        self.assertEqual(controller_truth["current_owner"]["state"], "degraded")
        self.assertEqual(controller_truth["current_lease"]["lease_id"], lease_id)
        self.assertEqual(controller_truth["current_lease"]["state"], "suspended")
        self.assertEqual(controller_truth["current_lease"]["intervention_reason"], "worker_state_degraded")
        self.assertEqual(controller_truth["pane_target"]["tmux_session"], "macs-test")
        self.assertEqual(controller_truth["pane_target"]["tmux_pane"], "%7")
        self.assertTrue(controller_truth["recent_event_refs"][0]["event_type"] in {"task.risk_hold_applied", "task.activated"})

    def test_task_inspect_json_surfaces_lock_summary_and_routing_rationale(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_degraded_worker_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        task = payload["task"]
        controller_truth = task["controller_truth"]

        self.assertEqual(controller_truth["routing_rationale_summary"]["decision_id"], "decision-inspect-001")
        self.assertEqual(controller_truth["routing_rationale_summary"]["selected_worker_id"], worker_id)
        self.assertIn("preserve current ownership", controller_truth["routing_rationale_summary"]["rationale"])
        self.assertEqual(controller_truth["lock_summary"]["active_lock_count"], 1)
        self.assertEqual(controller_truth["lock_summary"]["locks"][0]["lock_id"], "lock-inspect-001")
        self.assertEqual(controller_truth["lock_summary"]["locks"][0]["lease_id"], lease_id)

    def test_task_inspect_json_keeps_adapter_evidence_separate_from_controller_truth(self) -> None:
        self.init_repo()
        worker_id, task_id, _ = self.seed_degraded_worker_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        task = payload["task"]

        self.assertIn("controller_truth", task)
        self.assertIn("adapter_evidence", task)
        self.assertEqual(task["state"], "intervention_hold")
        self.assertEqual(task["controller_truth"]["current_owner"]["worker_id"], worker_id)
        self.assertEqual(task["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertGreaterEqual(len(task["adapter_evidence"]), 1)
        self.assertEqual(task["adapter_evidence"][0]["worker_id"], worker_id)
        self.assertEqual(task["adapter_evidence"][0]["kind"], "fact")
        self.assertEqual(task["adapter_evidence"][0]["name"], "pane_presence")

    def test_worker_inspect_human_readable_renders_controller_truth_before_adapter_evidence(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_degraded_worker_context()

        result = self.run_cli("worker", "inspect", "--worker", worker_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Worker: {worker_id}", output)
        self.assertIn("Warning: Worker worker-local-degraded is degraded", output)
        self.assertIn("Controller Truth:", output)
        self.assertIn("Canonical State: degraded", output)
        self.assertIn("Routability: blocked (worker_state_degraded)", output)
        self.assertIn(f"Current Task: {task_id} (intervention_hold)", output)
        self.assertIn(f"Current Lease: {lease_id} (suspended)", output)
        self.assertIn("Intervention Basis: worker_state_degraded", output)
        self.assertIn("Blocking Condition: current worker is degraded; controller suspended the live lease", output)
        self.assertIn(f"Next Action: reroute or recover task {task_id} before resume", output)
        self.assertIn("Recent Events:", output)
        self.assertIn("evt-worker-health-001  worker.health_reclassified", output)
        self.assertIn("Pane Target: macs-test %7", output)
        self.assertIn("Adapter Evidence:", output)
        self.assertIn("- fact pane_presence", output)
        self.assertLess(output.index("Controller Truth:"), output.index("Adapter Evidence:"))

    def test_task_inspect_human_readable_renders_owner_lease_lock_events_and_pane_target(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_degraded_worker_context()

        result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Task: {task_id}", output)
        self.assertIn("Warning: Task task-inspect-degraded is attached to degraded worker worker-local-degraded.", output)
        self.assertIn("Controller Truth:", output)
        self.assertIn(f"Current Owner: {worker_id} (degraded, local)", output)
        self.assertIn(f"Current Lease: {lease_id} (suspended)", output)
        self.assertIn("Intervention Basis: worker_state_degraded", output)
        self.assertIn("Blocking Condition: current worker is degraded; controller suspended the live lease", output)
        self.assertIn(f"Next Action: reroute or recover task {task_id} before resume", output)
        self.assertIn("Lock Summary: 1 active", output)
        self.assertIn("lock-inspect-001  docs/getting-started.md  held", output)
        self.assertIn("Routing Rationale: decision-inspect-001 -> worker-local-degraded", output)
        self.assertIn("Recent Events:", output)
        self.assertIn("evt-task-activated-001  task.activated", output)
        self.assertIn("Pane Target: macs-test %7", output)
        self.assertIn("Adapter Evidence:", output)
        self.assertIn("- fact pane_presence", output)
        self.assertLess(output.index("Controller Truth:"), output.index("Adapter Evidence:"))

    def test_task_inspect_surfaces_recent_checkpoint_refs_without_raw_file_browsing(self) -> None:
        self.init_repo()
        self.init_git_repo()
        create_result = self.run_cli("task", "create", "--summary", "Checkpoint inspect slice", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]
        self.create_checkpointable_repo_changes()

        checkpoint_result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.close",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(checkpoint_result.returncode, 0, checkpoint_result.stdout + checkpoint_result.stderr)
        checkpoint_payload = json.loads(checkpoint_result.stdout)
        checkpoint_id = checkpoint_payload["data"]["result"]["checkpoint_id"]

        json_result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        recent_checkpoints = payload["task"]["controller_truth"]["recent_checkpoint_refs"]
        self.assertEqual(recent_checkpoints[0]["checkpoint_id"], checkpoint_id)
        self.assertEqual(recent_checkpoints[0]["target_action"], "task.close")
        self.assertEqual(recent_checkpoints[0]["actor_id"], "operator.checkpoint@example.test")
        self.assertIn("bundle_dir", recent_checkpoints[0]["evidence_refs"])
        self.assertEqual(recent_checkpoints[0]["baseline_fingerprint"]["head"]["state"], "attached")
        self.assertGreaterEqual(len(recent_checkpoints[0]["baseline_fingerprint"]["affected_paths"]), 1)

        human_result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Recent Checkpoints:", human_result.stdout)
        self.assertIn(checkpoint_id, human_result.stdout)
        self.assertIn("task.close", human_result.stdout)
        self.assertIn("actor=operator.checkpoint@example.test", human_result.stdout)
        self.assertIn("bundle_dir=.codex/orchestration/checkpoints/", human_result.stdout)

    def test_task_inspect_json_surfaces_paused_state_intervention_basis_and_runtime_warning(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_paused_task_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task inspect")
        self.assertTrue(any("does not advertise pause/resume depth" in warning for warning in payload["warnings"]))

        task = payload["task"]
        self.assertEqual(task["task_id"], task_id)
        self.assertEqual(task["state"], "intervention_hold")
        self.assertEqual(task["runtime_intervention"]["status"], "controller_only")
        self.assertEqual(task["controller_truth"]["current_owner"]["worker_id"], worker_id)
        self.assertEqual(task["controller_truth"]["current_lease"]["lease_id"], lease_id)
        self.assertEqual(task["controller_truth"]["current_lease"]["state"], "paused")
        self.assertEqual(task["controller_truth"]["current_lease"]["intervention_reason"], "operator_pause")

    def test_event_inspect_json_surfaces_actor_rationale_and_affected_refs(self) -> None:
        self.init_repo()
        self.seed_paused_task_context()

        result = self.run_cli("event", "inspect", "--event", "evt-intervention-decision-pause-001", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        event = payload["data"]["event"]
        self.assertEqual(event["event_type"], "intervention.decision_recorded")
        self.assertEqual(event["actor_type"], "operator")
        self.assertEqual(event["actor_id"], "operator.pause@example.test")
        self.assertEqual(event["intervention_rationale"], "operator requested a safe in-place pause")
        self.assertEqual(event["affected_refs"]["task_id"], "task-inspect-paused")
        self.assertEqual(event["affected_refs"]["lease_id"], "lease-inspect-paused")

    def test_event_inspect_human_readable_surfaces_actor_rationale_and_affected_refs(self) -> None:
        self.init_repo()
        self.seed_paused_task_context()

        result = self.run_cli("event", "inspect", "--event", "evt-intervention-decision-pause-001")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("Event: evt-intervention-decision-pause-001", output)
        self.assertIn("Actor: operator operator.pause@example.test", output)
        self.assertIn("Intervention Rationale: operator requested a safe in-place pause", output)
        self.assertIn("Affected Refs: task=task-inspect-paused lease=lease-inspect-paused worker=worker-local-paused", output)

    def test_event_inspect_surfaces_checkpoint_target_action_and_artifact_linkage(self) -> None:
        self.init_repo()
        self.init_git_repo()
        create_result = self.run_cli("task", "create", "--summary", "Checkpoint event inspect slice", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]
        self.create_checkpointable_repo_changes()

        checkpoint_result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.archive",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(checkpoint_result.returncode, 0, checkpoint_result.stdout + checkpoint_result.stderr)
        event_id = json.loads(checkpoint_result.stdout)["data"]["event"]["event_id"]

        json_result = self.run_cli("event", "inspect", "--event", event_id, "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        event = payload["data"]["event"]
        checkpoint = payload["data"]["checkpoint"]
        self.assertEqual(event["event_type"], "review.checkpoint_recorded")
        self.assertEqual(event["actor_id"], "operator.checkpoint@example.test")
        self.assertEqual(event["target_action"], "task.archive")
        self.assertEqual(checkpoint["checkpoint_id"], event["checkpoint_id"])
        self.assertEqual(checkpoint["target_action"], "task.archive")
        self.assertIn("bundle_dir", checkpoint["evidence_refs"])
        self.assertEqual(checkpoint["baseline_fingerprint"]["head"]["state"], "attached")

        human_result = self.run_cli("event", "inspect", "--event", event_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn(f"Event: {event_id}", human_result.stdout)
        self.assertIn("Actor: operator operator.checkpoint@example.test", human_result.stdout)
        self.assertIn("Checkpoint: checkpoint-", human_result.stdout)
        self.assertIn("Target Action: task.archive", human_result.stdout)
        self.assertIn("Baseline Repo: head_state=attached", human_result.stdout)
        self.assertIn("Evidence Refs: bundle_dir=.codex/orchestration/checkpoints/", human_result.stdout)

    def test_event_inspect_traces_gated_archive_to_checkpoint_and_decision_event(self) -> None:
        self.init_repo()
        self.init_git_repo()
        task_id = self.seed_completed_task()
        self.create_checkpointable_repo_changes()

        checkpoint_result = self.run_cli(
            "task",
            "checkpoint",
            "--task",
            task_id,
            "--target-action",
            "task.archive",
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(checkpoint_result.returncode, 0, checkpoint_result.stdout + checkpoint_result.stderr)
        checkpoint_id = json.loads(checkpoint_result.stdout)["data"]["result"]["checkpoint_id"]

        archive_result = self.run_cli(
            "task",
            "archive",
            "--task",
            task_id,
            "--json",
            env_overrides={"MACS_OPERATOR_ID": "operator.checkpoint@example.test"},
        )
        self.assertEqual(archive_result.returncode, 0, archive_result.stdout + archive_result.stderr)
        archive_payload = json.loads(archive_result.stdout)
        event_id = archive_payload["data"]["event"]["event_id"]
        decision_event_id = archive_payload["data"]["result"]["decision_event_id"]

        json_result = self.run_cli("event", "inspect", "--event", event_id, "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        self.assertEqual(payload["data"]["event"]["event_type"], "task.archived")
        self.assertEqual(payload["data"]["event"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(payload["data"]["event"]["decision_event_id"], decision_event_id)
        self.assertEqual(payload["data"]["checkpoint"]["checkpoint_id"], checkpoint_id)
        self.assertEqual(payload["data"]["checkpoint"]["target_action"], "task.archive")
        self.assertEqual(payload["data"]["decision_event"]["event_id"], decision_event_id)
        self.assertEqual(payload["data"]["decision_event"]["actor_id"], "operator.checkpoint@example.test")
        self.assertEqual(payload["data"]["decision_event"]["checkpoint_id"], checkpoint_id)

        human_result = self.run_cli("event", "inspect", "--event", event_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn(f"Event: {event_id}", human_result.stdout)
        self.assertIn(f"Checkpoint: {checkpoint_id}", human_result.stdout)
        self.assertIn(f"Decision Event: {decision_event_id}", human_result.stdout)
        self.assertIn("Decision Actor: operator.checkpoint@example.test", human_result.stdout)

    def test_task_inspect_json_surfaces_compact_governance_evidence_without_secret_leakage(self) -> None:
        scenario = self.seed_governed_task_context()

        json_result = self.run_cli("task", "inspect", "--task", scenario["task_id"], "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        evidence = payload["task"]["governance_evidence"]
        self.assertEqual(evidence["policy"]["policy_version"], "phase1-governance-v1")
        self.assertTrue(evidence["policy"]["policy_path"].endswith("governance-policy.json"))
        self.assertEqual(evidence["policy"]["snapshot"]["traceability_status"], "stale_vs_live_policy")
        self.assertEqual(evidence["routing"]["selected_worker_id"], "worker-codex-governed-inspect")
        self.assertEqual(evidence["routing"]["related_event_id"], scenario["assign_event_id"])

        version_pin = evidence["version_pins"]["surface_results"][0]
        self.assertEqual(version_pin["surface_id"], "mcp")
        self.assertEqual(version_pin["outcome"], "matched")
        self.assertEqual(version_pin["selector_context"]["adapter_id"], "codex")
        self.assertEqual(version_pin["expected"]["model_identities"], ["gpt-5.4"])
        self.assertEqual(version_pin["observed"]["model_identity"]["identity"], "gpt-5.4")

        secret_scope = evidence["secret_scope"]["surface_results"][0]
        self.assertEqual(secret_scope["surface_id"], "mcp")
        self.assertEqual(secret_scope["outcome"], "resolved")
        self.assertEqual(secret_scope["secret_ref"], "mcp.codex.token")
        self.assertEqual(secret_scope["selector_context"]["workflow_class"], "implementation")

        checkpoint = evidence["checkpoint"]
        self.assertEqual(checkpoint["checkpoint_id"], scenario["checkpoint_id"])
        self.assertEqual(checkpoint["target_action"], "task.close")
        self.assertEqual(checkpoint["actor_id"], "operator.governance@example.test")
        self.assertIn("head_state=attached", checkpoint["baseline_summary"])

        self.assertNotIn(scenario["runtime_secret"], json.dumps(evidence, sort_keys=True))

        human_result = self.run_cli("task", "inspect", "--task", scenario["task_id"])
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Governance Evidence:", human_result.stdout)
        self.assertIn("Policy Traceability:", human_result.stdout)
        self.assertIn("Version Pin Evidence:", human_result.stdout)
        self.assertIn("Secret Scope Evidence:", human_result.stdout)
        self.assertIn("Checkpoint Evidence:", human_result.stdout)
        self.assertIn("mcp.codex.token", human_result.stdout)
        self.assertNotIn(scenario["runtime_secret"], human_result.stdout)

    def test_task_inspect_governance_evidence_read_leaves_governance_policy_unchanged(self) -> None:
        scenario = self.seed_governed_task_context()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["secret_scopes"][0]["secret_value"] = {"inline_field_present": True}
        governance_policy["secret_scopes"][0]["password"] = ["keep-on-disk-for-write-side-tests"]
        original_policy_text = json.dumps(governance_policy, indent=2, sort_keys=True) + "\n"
        governance_path.write_text(original_policy_text, encoding="utf-8")

        json_result = self.run_cli("task", "inspect", "--task", scenario["task_id"], "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        self.assertNotIn("secret_value", json_result.stdout)
        self.assertNotIn("password", json_result.stdout)

        self.assertEqual(governance_path.read_text(encoding="utf-8"), original_policy_text)

    def test_event_inspect_surfaces_governance_evidence_and_decision_linkage_without_secret_leakage(self) -> None:
        scenario = self.seed_governed_task_context(close_task=True)

        json_result = self.run_cli("event", "inspect", "--event", scenario["close_event_id"], "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        evidence = payload["data"]["governance_evidence"]
        self.assertEqual(evidence["routing"]["selected_worker_id"], "worker-codex-governed-inspect")
        self.assertEqual(evidence["routing"]["related_event_id"], scenario["assign_event_id"])
        self.assertEqual(evidence["checkpoint"]["checkpoint_id"], scenario["checkpoint_id"])
        self.assertEqual(evidence["checkpoint"]["decision_event_id"], scenario["decision_event_id"])
        self.assertEqual(evidence["decision_event"]["event_id"], scenario["decision_event_id"])
        self.assertEqual(evidence["version_pins"]["surface_results"][0]["observed"]["model_identity"]["identity"], "gpt-5.4")
        self.assertEqual(evidence["secret_scope"]["surface_results"][0]["secret_ref"], "mcp.codex.token")
        self.assertNotIn(scenario["runtime_secret"], json.dumps(payload["data"], sort_keys=True))

        human_result = self.run_cli("event", "inspect", "--event", scenario["close_event_id"])
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Governance Evidence:", human_result.stdout)
        self.assertIn(f"Decision Event: {scenario['decision_event_id']}", human_result.stdout)
        self.assertIn("Version Pin Evidence:", human_result.stdout)
        self.assertIn("Secret Scope Evidence:", human_result.stdout)
        self.assertIn("Checkpoint Evidence:", human_result.stdout)
        self.assertNotIn(scenario["runtime_secret"], human_result.stdout)

    def test_task_inspect_surfaces_version_pin_rejection_governance_evidence(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        self.configure_surface_version_pin(
            adapter_id="codex",
            expected_runtime_identity="codex",
            expected_model_identity="gpt-5.4",
        )
        socket = self.temp_dir / "version-mismatch-inspect.sock"
        session = f"version-mismatch-inspect-{os.getpid()}"
        pane_id = self.create_tmux_session(socket, session, window_name="codex")
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.stage_tmux_capture(socket, pane_id, "codex --model gpt-5.4-mini --sandbox workspace-write --yolo")
        self.seed_worker_row(
            worker_id="worker-codex-version-mismatch-inspect",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            operator_tags=["registered", "surface:mcp"],
            tmux_socket=str(socket),
            tmux_session=session,
            tmux_pane=pane_id,
        )
        create_result = self.run_cli("task", "create", "--summary", "Version mismatch inspect", "--json")
        self.assertEqual(create_result.returncode, 0, create_result.stderr)
        task_id = json.loads(create_result.stdout)["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 4, assign_result.stdout + assign_result.stderr)

        inspect_result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        payload = json.loads(inspect_result.stdout)

        evidence = payload["task"]["governance_evidence"]
        self.assertEqual(evidence["routing"]["selected_worker_id"], "none")
        version_pin = evidence["version_pins"]["surface_results"][0]
        self.assertEqual(version_pin["outcome"], "blocked")
        self.assertEqual(version_pin["reason"], "surface_version_pin_mismatch")
        self.assertEqual(version_pin["expected"]["model_identities"], ["gpt-5.4"])
        self.assertEqual(version_pin["observed"]["model_identity"]["identity"], "gpt-5.4-mini")

        human_result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Governance Evidence:", human_result.stdout)
        self.assertIn("surface_version_pin_mismatch", human_result.stdout)
        self.assertIn("gpt-5.4-mini", human_result.stdout)

    def test_task_inspect_surfaces_audit_safe_secret_resolution_metadata_without_raw_values(self) -> None:
        task_id, _, runtime_secret = self.assign_secret_backed_task()

        json_result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        secret_resolution = payload["task"]["secret_resolution"]
        self.assertEqual(secret_resolution["status"], "resolved")
        self.assertEqual(secret_resolution["resolved_secret_refs"], ["mcp.codex.token"])
        self.assertEqual(secret_resolution["surface_summaries"][0]["selector_context"]["surface_id"], "mcp")
        self.assertNotIn(runtime_secret, json.dumps(secret_resolution, sort_keys=True))

        human_result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Secret Resolution: resolved", human_result.stdout)
        self.assertIn("mcp.codex.token", human_result.stdout)
        self.assertNotIn(runtime_secret, human_result.stdout)

    def test_event_inspect_surfaces_secret_resolution_metadata_without_raw_values(self) -> None:
        _, event_id, runtime_secret = self.assign_secret_backed_task()

        json_result = self.run_cli("event", "inspect", "--event", event_id, "--json")
        self.assertEqual(json_result.returncode, 0, json_result.stderr)
        payload = json.loads(json_result.stdout)

        secret_resolution = payload["data"]["event"]["payload"]["secret_resolution"]
        self.assertEqual(secret_resolution["resolved_secret_refs"], ["mcp.codex.token"])
        self.assertEqual(secret_resolution["surface_summaries"][0]["surface_id"], "mcp")
        self.assertNotIn(runtime_secret, json.dumps(payload["data"]["event"], sort_keys=True))

        human_result = self.run_cli("event", "inspect", "--event", event_id)
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Secret Resolution: resolved", human_result.stdout)
        self.assertIn("mcp.codex.token", human_result.stdout)
        self.assertNotIn(runtime_secret, human_result.stdout)

    def test_adapter_inspect_json_surfaces_governed_surface_policy(self) -> None:
        self.init_repo()

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        self.assertEqual(governance["policy_version"], "phase1-governance-v1")
        self.assertEqual(governance["declared_surfaces"][0]["surface_id"], "mcp")
        self.assertFalse(governance["declared_surfaces"][0]["allowlisted"])

    def test_adapter_inspect_json_surfaces_applicable_surface_version_pin_policy(self) -> None:
        self.init_repo()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["surface_version_pins"] = [
            {
                "surface_id": "mcp",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "expected_runtime_identity": "codex",
                "expected_model_identity": "gpt-5.4",
            },
            {
                "surface_id": "mcp",
                "adapter_id": "claude",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "expected_runtime_identity": "claude",
                "expected_model_identity": "claude-3-7-sonnet",
            },
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        self.assertEqual(governance["operating_profile"], "primary_plus_fallback")
        self.assertEqual(governance["surface_version_pins"]["effective_state"], "pins_apply")
        self.assertEqual(len(governance["surface_version_pins"]["effective_pins"]), 1)
        self.assertEqual(governance["surface_version_pins"]["effective_pins"][0]["expected_model_identity"], "gpt-5.4")
        self.assertEqual(
            governance["declared_surfaces"][0]["applicable_version_pins"][0]["expected_runtime_identity"],
            "codex",
        )

    def test_adapter_inspect_json_surfaces_applicable_secret_scope_policy(self) -> None:
        self.init_repo()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["secret_scopes"] = [
            {
                "surface_id": "mcp",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "secret_ref": "mcp.codex.token",
                "display_name": "Codex MCP token",
                "redaction_label": "masked",
                "secret_value": {"inline_field_present": True},
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
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        self.assertEqual(governance["secret_scopes"]["effective_state"], "scopes_apply")
        self.assertEqual(len(governance["secret_scopes"]["effective_scopes"]), 1)
        scope = governance["secret_scopes"]["effective_scopes"][0]
        self.assertEqual(scope["secret_ref"], "mcp.codex.token")
        self.assertEqual(scope["display_name"], "Codex MCP token")
        self.assertEqual(scope["redaction_label"], "masked")
        self.assertNotIn("secret_value", scope)
        self.assertEqual(
            governance["declared_surfaces"][0]["applicable_secret_scopes"][0]["secret_ref"],
            "mcp.codex.token",
        )

        human_result = self.run_cli("adapter", "inspect", "--adapter", "codex")
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Secret scopes:", human_result.stdout)
        self.assertIn("mcp.codex.token", human_result.stdout)
        self.assertNotIn("secret_value", human_result.stdout)

    def test_adapter_inspect_json_excludes_non_matching_secret_scopes_from_top_level_summary(self) -> None:
        self.init_repo()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["secret_scopes"] = [
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
                "surface_id": "shell",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "secret_ref": "shell.codex.token",
                "display_name": "Codex shell token",
                "redaction_label": "masked",
            },
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        self.assertEqual(
            [scope["surface_id"] for scope in governance["secret_scopes"]["normalized_scopes"]],
            ["mcp"],
        )
        self.assertEqual(
            [scope["surface_id"] for scope in governance["secret_scopes"]["effective_scopes"]],
            ["mcp"],
        )
        self.assertEqual(
            [scope["surface_id"] for scope in governance["declared_surfaces"][0]["applicable_secret_scopes"]],
            ["mcp"],
        )

    def test_adapter_inspect_json_excludes_undeclared_surface_pins_from_top_level_summary(self) -> None:
        self.init_repo()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["surface_version_pins"] = [
            {
                "surface_id": "mcp",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "expected_runtime_identity": "codex",
                "expected_model_identity": "gpt-5.4",
            },
            {
                "surface_id": "shell",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "expected_runtime_identity": "codex",
                "expected_model_identity": "gpt-5.4-mini",
            },
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        self.assertEqual(
            [pin["surface_id"] for pin in governance["surface_version_pins"]["normalized_pins"]],
            ["mcp"],
        )
        self.assertEqual(
            [pin["surface_id"] for pin in governance["surface_version_pins"]["effective_pins"]],
            ["mcp"],
        )
        self.assertEqual(
            [pin["surface_id"] for pin in governance["declared_surfaces"][0]["applicable_version_pins"]],
            ["mcp"],
        )

    def test_adapter_inspect_json_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit(self) -> None:
        self.init_repo()

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        governance_policy["surface_version_pins"] = [
            {
                "surface_id": "mcp",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "primary_plus_fallback",
                "expected_runtime_identity": "codex",
                "expected_model_identity": "gpt-5.4",
            }
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance = payload["data"]["governance"]
        active_snapshot = governance["active_snapshot"]
        self.assertEqual(active_snapshot["traceability_status"], "stale_vs_live_policy")
        self.assertFalse(active_snapshot["matches_live_policy"])
        self.assertEqual(active_snapshot["surface_version_pins"]["state"], "none_configured")
        self.assertEqual(governance["surface_version_pins"]["effective_state"], "pins_apply")

        human_result = self.run_cli("adapter", "inspect", "--adapter", "codex")
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("stale relative to live governance policy", human_result.stdout)
        self.assertIn("Snapshot-captured surface version pins: none configured", human_result.stdout)

    def test_event_inspect_human_readable_surfaces_redaction_level_and_audit_content_status(self) -> None:
        self.init_repo()
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")
        tmux_dir = self.temp_dir / "tmux-event-redaction"
        tmux_dir.mkdir(exist_ok=True)
        socket = tmux_dir / "event-redaction.sock"
        session = f"macs-event-redaction-{os.getpid()}"
        pane_id = self.create_tmux_session(socket, session, window_name="codex")
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.seed_worker_row(
            worker_id="worker-codex-event-redaction",
            runtime_type="codex",
            adapter_id="codex",
            capabilities=["implementation"],
            tmux_socket=str(socket),
            tmux_session=session,
            tmux_pane=pane_id,
        )
        create_payload = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Inspect redacted event",
                "--workflow-class",
                "implementation",
                "--require-capability",
                "implementation",
                "--surface",
                "docs/redaction.md",
                "--json",
            ).stdout
        )
        task_id = create_payload["data"]["result"]["task"]["task_id"]
        assign_payload = json.loads(self.run_cli("task", "assign", "--task", task_id, "--json").stdout)
        event_id = assign_payload["data"]["event"]["event_id"]

        result = self.run_cli("event", "inspect", "--event", event_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Event: {event_id}", output)
        self.assertIn("Redaction Level: omitted", output)
        self.assertIn("Audit Content:", output)
        self.assertIn("- prompt_content: omitted", output)

    def test_event_list_json_surfaces_causation_rationale_and_affected_refs(self) -> None:
        self.init_repo()
        self.seed_paused_task_context()

        result = self.run_cli("event", "list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        decision_event = next(
            event for event in payload["data"]["events"] if event["event_id"] == "evt-intervention-decision-pause-001"
        )
        self.assertEqual(decision_event["actor_id"], "operator.pause@example.test")
        self.assertIsNone(decision_event["causation_id"])
        self.assertEqual(decision_event["intervention_rationale"], "operator requested a safe in-place pause")
        self.assertEqual(decision_event["affected_refs"]["task_id"], "task-inspect-paused")

    def test_event_list_human_readable_surfaces_actor_and_rationale(self) -> None:
        self.init_repo()
        self.seed_paused_task_context()

        result = self.run_cli("event", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "evt-intervention-decision-pause-001  intervention.decision_recorded  task:task-inspect-paused  actor=operator.pause@example.test  rationale=operator requested a safe in-place pause",
            result.stdout,
        )

    def test_task_inspect_json_recent_events_surface_actor_rationale_and_causation(self) -> None:
        self.init_repo()
        self.seed_paused_task_context()

        result = self.run_cli("task", "inspect", "--task", "task-inspect-paused", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        recent_events = payload["task"]["controller_truth"]["recent_event_refs"]
        decision_event = next(event for event in recent_events if event["event_id"] == "evt-intervention-decision-pause-001")
        self.assertEqual(decision_event["actor_id"], "operator.pause@example.test")
        self.assertEqual(decision_event["intervention_rationale"], "operator requested a safe in-place pause")

        task_paused_event = next(event for event in recent_events if event["event_id"] == "evt-task-paused-001")
        self.assertEqual(task_paused_event["causation_id"], "evt-lease-paused-001")
        self.assertEqual(task_paused_event["decision_event_id"], "evt-intervention-decision-pause-001")

    def test_task_inspect_human_readable_renders_paused_lease_basis_and_runtime_warning(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_paused_task_context()

        result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Task: {task_id}", output)
        self.assertIn("State: intervention_hold", output)
        self.assertIn(f"Current Lease: {lease_id} (paused)", output)
        self.assertIn("Intervention Basis: operator_pause", output)
        self.assertIn("Runtime Pause Depth: controller_only", output)
        self.assertIn(f"Next Action: macs task resume --task {task_id}", output)
        self.assertIn("Warning: Adapter local does not advertise pause/resume depth", output)
        self.assertIn(
            "evt-intervention-decision-pause-001  intervention.decision_recorded  actor=operator.pause@example.test",
            output,
        )
        self.assertIn("rationale=operator requested a safe in-place pause", output)

    def test_lease_inspect_human_readable_renders_pause_basis_and_runtime_warning(self) -> None:
        self.init_repo()
        _, _, lease_id = self.seed_paused_task_context()

        result = self.run_cli("lease", "inspect", "--lease", lease_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Lease: {lease_id}", output)
        self.assertIn("State: paused", output)
        self.assertIn("Issued At:", output)
        self.assertIn("Accepted At:", output)
        self.assertIn("Replacement Lease: none", output)
        self.assertIn("Intervention Basis: operator_pause", output)
        self.assertIn("Runtime Pause Depth: controller_only", output)
        self.assertIn("Warning: Adapter local does not advertise pause/resume depth", output)

    def test_lease_inspect_json_surfaces_latest_decision_actor_rationale_and_recent_event(self) -> None:
        self.init_repo()
        _, _, lease_id = self.seed_paused_task_context()

        result = self.run_cli("lease", "inspect", "--lease", lease_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        decision_event = payload["data"]["decision_event"]
        self.assertEqual(decision_event["event_id"], "evt-intervention-decision-pause-001")
        self.assertEqual(decision_event["actor_id"], "operator.pause@example.test")
        self.assertEqual(decision_event["intervention_rationale"], "operator requested a safe in-place pause")
        self.assertEqual(payload["data"]["recent_event_refs"][0]["event_id"], "evt-lease-paused-001")
        self.assertEqual(
            payload["data"]["recent_event_refs"][0]["decision_event_id"],
            "evt-intervention-decision-pause-001",
        )

    def test_lease_history_json_surfaces_latest_event_causation_and_decision_context(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_paused_task_context()

        result = self.run_cli("lease", "history", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        lease = next(item for item in payload["data"]["leases"] if item["lease_id"] == lease_id)
        self.assertEqual(lease["latest_event_ref"]["event_id"], "evt-lease-paused-001")
        self.assertEqual(lease["latest_event_ref"]["causation_id"], "evt-intervention-decision-pause-001")
        self.assertEqual(lease["decision_event"]["actor_id"], "operator.pause@example.test")

    def test_lease_history_human_readable_surfaces_latest_event_and_decision_actor(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_paused_task_context()

        result = self.run_cli("lease", "history", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"{lease_id}  task-inspect-paused  worker-local-paused  paused  latest=evt-lease-paused-001  cause=evt-intervention-decision-pause-001  actor=operator.pause@example.test",
            result.stdout,
        )

    def test_task_inspect_json_surfaces_suspended_state_intervention_basis_and_next_action(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs task inspect")
        self.assertIn(
            f"Task {task_id} is attached to degraded worker {worker_id}.",
            payload["warnings"],
        )

        task = payload["task"]
        self.assertEqual(task["task_id"], task_id)
        self.assertEqual(task["state"], "intervention_hold")
        self.assertEqual(task["controller_truth"]["current_owner"]["worker_id"], worker_id)
        self.assertEqual(task["controller_truth"]["current_lease"]["lease_id"], lease_id)
        self.assertEqual(task["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(task["controller_truth"]["current_lease"]["intervention_reason"], "worker_state_degraded")
        self.assertEqual(
            task["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(task["next_action"], f"reroute or recover task {task_id} before resume")

    def test_task_inspect_human_readable_renders_suspended_lease_basis_and_next_action(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Task: {task_id}", output)
        self.assertIn("State: intervention_hold", output)
        self.assertIn(f"Current Lease: {lease_id} (suspended)", output)
        self.assertIn("Intervention Basis: worker_state_degraded", output)
        self.assertIn("Blocking Condition: current worker is degraded; controller suspended the live lease", output)
        self.assertIn(f"Next Action: reroute or recover task {task_id} before resume", output)
        self.assertNotIn("Runtime Pause Depth:", output)

    def test_lease_inspect_human_readable_renders_suspension_basis_without_runtime_pause_depth(self) -> None:
        self.init_repo()
        _, _, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("lease", "inspect", "--lease", lease_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Lease: {lease_id}", output)
        self.assertIn("State: suspended", output)
        self.assertIn("Intervention Basis: worker_state_degraded", output)
        self.assertIn("Blocking Condition: current worker is degraded; controller suspended the live lease", output)
        self.assertIn("Next Action: reroute or recover task task-inspect-suspended before resume", output)
        self.assertNotIn("Runtime Pause Depth:", output)

    def test_lease_inspect_json_surfaces_suspended_blocking_condition_and_next_action(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("lease", "inspect", "--lease", lease_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["lease"]["lease_id"], lease_id)
        self.assertEqual(payload["data"]["lease"]["state"], "suspended")
        self.assertEqual(
            payload["data"]["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(
            payload["data"]["next_action"],
            f"reroute or recover task {task_id} before resume",
        )

    def test_worker_inspect_json_surfaces_suspended_current_task_and_next_action(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("worker", "inspect", "--worker", worker_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ok"])
        worker = payload["worker"]
        self.assertEqual(worker["worker_id"], worker_id)
        self.assertEqual(
            worker["controller_truth"]["current_task"]["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(worker["next_action"], f"reroute or recover task {task_id} before resume")
        self.assertEqual(worker["controller_truth"]["current_task"]["task_id"], task_id)
        self.assertEqual(worker["controller_truth"]["current_task"]["state"], "intervention_hold")
        self.assertEqual(worker["controller_truth"]["current_lease"]["lease_id"], lease_id)
        self.assertEqual(worker["controller_truth"]["current_lease"]["state"], "suspended")
        self.assertEqual(
            worker["controller_truth"]["current_lease"]["intervention_reason"],
            "worker_state_degraded",
        )

    def test_worker_inspect_human_readable_renders_suspended_task_basis_and_next_action(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("worker", "inspect", "--worker", worker_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Worker: {worker_id}", output)
        self.assertIn(f"Current Task: {task_id} (intervention_hold)", output)
        self.assertIn(f"Current Lease: {lease_id} (suspended)", output)
        self.assertIn("Intervention Basis: worker_state_degraded", output)
        self.assertIn("Blocking Condition: current worker is degraded; controller suspended the live lease", output)
        self.assertIn(f"Next Action: reroute or recover task {task_id} before resume", output)

    def test_overview_show_json_surfaces_suspended_hold_details_and_next_action(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id = self.seed_suspended_task_context()

        result = self.run_cli("overview", "show", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        overview = payload["data"]["overview"]
        self.assertEqual(overview["task_summary"]["intervention_hold"], 1)
        self.assertTrue(
            any(
                alert["kind"] == "task_hold"
                and alert["task_id"] == task_id
                and alert["lease_state"] == "suspended"
                and alert["blocking_condition"] == "current worker is degraded; controller suspended the live lease"
                and alert["next_action"] == f"reroute or recover task {task_id} before resume"
                for alert in overview["active_alerts"]
            )
        )
        self.assertEqual(overview["active_tasks"][0]["task_id"], task_id)
        self.assertEqual(overview["active_tasks"][0]["current_worker_id"], worker_id)
        self.assertEqual(overview["active_tasks"][0]["current_lease_id"], lease_id)
        self.assertEqual(overview["active_tasks"][0]["lease_state"], "suspended")
        self.assertEqual(overview["active_tasks"][0]["intervention_reason"], "worker_state_degraded")
        self.assertEqual(
            overview["active_tasks"][0]["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(
            overview["active_tasks"][0]["next_action"],
            f"reroute or recover task {task_id} before resume",
        )

    def test_overview_show_human_readable_renders_suspended_hold_summary_and_next_action(self) -> None:
        self.init_repo()
        _, task_id, _ = self.seed_suspended_task_context()

        result = self.run_cli("overview", "show")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("Active alerts:", output)
        self.assertIn("Held Tasks:", output)
        self.assertIn(f"{task_id}  intervention_hold  lease=suspended", output)
        self.assertIn("basis=worker_state_degraded", output)
        self.assertIn("blocking=current worker is degraded; controller suspended the live lease", output)
        self.assertIn(f"next=reroute or recover task {task_id} before resume", output)

    def test_recovery_inspect_json_surfaces_anomaly_current_and_proposed_state(self) -> None:
        self.init_repo()
        worker_id, task_id, lease_id, recovery_run_id = self.seed_recovery_run_context()

        result = self.run_cli("recovery", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs recovery inspect")
        self.assertEqual(payload["warnings"], [])
        self.assertEqual(payload["errors"], [])

        recovery = payload["data"]["recovery"]
        self.assertEqual(recovery["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(recovery["recovery_run"]["state"], "pending_operator_action")
        self.assertEqual(recovery["anomaly_summary"]["kind"], "ambiguous_ownership")
        self.assertEqual(recovery["current_state"]["task_id"], task_id)
        self.assertEqual(recovery["current_state"]["task_state"], "intervention_hold")
        self.assertEqual(recovery["current_state"]["current_worker_id"], worker_id)
        self.assertEqual(recovery["current_state"]["current_lease_id"], lease_id)
        self.assertEqual(recovery["proposed_state"]["selected_worker_id"], "worker-local-recovery-target")
        self.assertEqual(recovery["proposed_state"]["workflow_class"], "analysis")
        self.assertEqual(
            recovery["blocking_condition"],
            "current worker is degraded; controller suspended the live lease",
        )
        self.assertEqual(
            recovery["allowed_next_actions"][0],
            f"macs task reroute --task {task_id} --worker worker-local-recovery-target",
        )
        self.assertEqual(recovery["latest_intervention_decision"]["event_id"], "evt-intervention-decision-recovery-001")
        self.assertEqual(
            recovery["latest_intervention_decision"]["actor_id"],
            "operator.recovery@example.test",
        )
        self.assertEqual(
            recovery["latest_intervention_decision"]["intervention_rationale"],
            "operator approved a controlled reroute after degraded ownership",
        )
        self.assertEqual(recovery["recent_event_refs"][0]["event_id"], "evt-recovery-reroute-requested-001")
        self.assertEqual(
            recovery["recent_event_refs"][0]["decision_event_id"],
            "evt-intervention-decision-recovery-001",
        )

    def test_recovery_inspect_human_readable_surfaces_anomaly_current_and_proposed_state(self) -> None:
        self.init_repo()
        _, task_id, lease_id, recovery_run_id = self.seed_recovery_run_context()

        result = self.run_cli("recovery", "inspect", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Recovery Run: {recovery_run_id}", output)
        self.assertIn("State: pending_operator_action", output)
        self.assertIn("Anomaly Summary: ambiguous_ownership", output)
        self.assertIn(f"Task: {task_id}", output)
        self.assertIn("Task State: intervention_hold", output)
        self.assertIn(f"Current Lease: {lease_id}", output)
        self.assertIn("Decision Actor: operator.recovery@example.test", output)
        self.assertIn(
            "Intervention Rationale: operator approved a controlled reroute after degraded ownership",
            output,
        )
        self.assertIn("Proposed Worker: worker-local-recovery-target", output)
        self.assertIn("Proposed Workflow Class: analysis", output)
        self.assertIn("Allowed Next Actions:", output)
        self.assertIn(f"macs task reroute --task {task_id} --worker worker-local-recovery-target", output)

    def test_task_inspect_json_surfaces_recovery_run_status_for_held_task(self) -> None:
        self.init_repo()
        _, task_id, _, recovery_run_id = self.seed_recovery_run_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        task = payload["task"]
        self.assertEqual(task["controller_truth"]["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(task["controller_truth"]["recovery_run"]["state"], "pending_operator_action")

    def test_overview_show_json_surfaces_recovery_run_status_for_held_task(self) -> None:
        self.init_repo()
        _, task_id, _, recovery_run_id = self.seed_recovery_run_context()

        result = self.run_cli("overview", "show", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        held_task = next(task for task in payload["data"]["overview"]["active_tasks"] if task["task_id"] == task_id)
        self.assertEqual(held_task["recovery_run_state"], "pending_operator_action")
        self.assertEqual(held_task["recovery_run_id"], recovery_run_id)

    def test_task_inspect_human_readable_surfaces_recovery_run_status_for_held_task(self) -> None:
        self.init_repo()
        _, task_id, _, recovery_run_id = self.seed_recovery_run_context()

        result = self.run_cli("task", "inspect", "--task", task_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"Recovery Run: {recovery_run_id} (pending_operator_action)", output)

    def test_overview_show_human_readable_surfaces_recovery_run_status_for_held_task(self) -> None:
        self.init_repo()
        _, task_id, _, _ = self.seed_recovery_run_context()

        result = self.run_cli("overview", "show")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn(f"{task_id}  intervention_hold  lease=suspended", output)
        self.assertIn("recovery=pending_operator_action", output)

    def test_task_inspect_json_surfaces_next_action_for_interrupted_recovery_without_live_lease(self) -> None:
        self.init_repo()
        task_id, recovery_run_id = self.seed_interrupted_recovery_context()

        result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        task = payload["task"]
        self.assertEqual(task["state"], "reconciliation")
        self.assertEqual(task["controller_truth"]["recovery_run"]["recovery_run_id"], recovery_run_id)
        self.assertEqual(task["controller_truth"]["recovery_run"]["state"], "pending_retry")
        self.assertEqual(
            task["blocking_condition"],
            "interrupted recovery run is blocking successor routing",
        )
        self.assertEqual(task["next_action"], f"macs recovery retry --task {task_id}")

    def test_overview_show_human_readable_surfaces_interrupted_recovery_without_live_lease(self) -> None:
        self.init_repo()
        task_id, _ = self.seed_interrupted_recovery_context()

        result = self.run_cli("overview", "show")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = result.stdout

        self.assertIn("Recovery Tasks:", output)
        self.assertIn(f"{task_id}  reconciliation  lease=none", output)
        self.assertIn("recovery=pending_retry", output)
        self.assertIn(
            f"next=macs recovery retry --task {task_id}",
            output,
        )

    def test_task_inspect_human_readable_stacks_paused_fields_on_narrow_no_color_terminals(self) -> None:
        self.init_repo()
        _, task_id, lease_id = self.seed_paused_task_context()

        result = self.run_cli(
            "task",
            "inspect",
            "--task",
            task_id,
            env_overrides={"COLUMNS": "80", "NO_COLOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotRegex(result.stdout, r"\x1b\[[0-9;]*m")
        self.assertIn(f"Task:\n  {task_id}", result.stdout)
        self.assertIn("Current Owner:\n  worker-local-paused (ready, local)", result.stdout)
        self.assertIn(f"Current Lease:\n  {lease_id} (paused)", result.stdout)
        self.assertIn("Intervention Basis:\n  operator_pause", result.stdout)
        self.assertIn(f"Next Action:\n  macs task resume --task {task_id}", result.stdout)

    def test_lease_inspect_human_readable_stacks_pause_fields_on_narrow_terminal(self) -> None:
        self.init_repo()
        _, _, lease_id = self.seed_paused_task_context()

        result = self.run_cli(
            "lease",
            "inspect",
            "--lease",
            lease_id,
            env_overrides={"COLUMNS": "80", "NO_COLOR": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotRegex(result.stdout, r"\x1b\[[0-9;]*m")
        self.assertIn(f"Lease:\n  {lease_id}", result.stdout)
        self.assertIn("Replacement Lease:\n  none", result.stdout)
        self.assertIn("Intervention Basis:\n  operator_pause", result.stdout)
        self.assertIn("Runtime Pause Depth:\n  controller_only", result.stdout)

    def test_worker_inspect_open_pane_json_pins_target_and_warns_when_live_jump_unavailable(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        worker_id, _, _ = self.seed_degraded_worker_context()

        result = self.run_cli("worker", "inspect", "--worker", worker_id, "--open-pane", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(self.read_target_pane(), "%7")
        self.assertEqual(payload["worker"]["pane_navigation"]["status"], "pinned_only")
        self.assertEqual(payload["worker"]["pane_navigation"]["tmux_session"], "macs-test")
        self.assertEqual(payload["worker"]["pane_navigation"]["tmux_pane"], "%7")
        self.assertIn(
            "Unable to open tmux pane live; pinned target macs-test %7 for follow-up.",
            payload["warnings"],
        )

    def test_task_inspect_open_pane_json_reports_opened_on_matching_tmux_server(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.init_repo()
        tmux_dir = self.temp_dir / "tmux-open-pane"
        tmux_dir.mkdir()
        socket = tmux_dir / "inspect.sock"
        worker_session = f"macs-worker-{os.getpid()}"
        runner_session = f"macs-controller-{os.getpid()}"
        worker_pane = self.create_tmux_session(socket, worker_session, window_name="worker")
        _, task_id, _ = self.seed_degraded_worker_context(
            tmux_socket=str(socket),
            tmux_session=worker_session,
            tmux_pane=worker_pane,
        )

        try:
            result = self.run_cli_in_tmux(
                socket,
                runner_session,
                "task",
                "inspect",
                "--task",
                task_id,
                "--open-pane",
                "--json",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)

            self.assertEqual(self.read_target_pane(), worker_pane)
            self.assertEqual(payload["task"]["pane_navigation"]["status"], "opened")
            self.assertEqual(payload["task"]["pane_navigation"]["tmux_session"], worker_session)
            self.assertEqual(payload["task"]["pane_navigation"]["tmux_pane"], worker_pane)
            self.assertNotIn(
                "Unable to open tmux pane live; pinned target "
                f"{worker_session} {worker_pane} for follow-up.",
                payload["warnings"],
            )
        finally:
            subprocess.run(
                ["tmux", "-S", str(socket), "kill-server"],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_common_sh_reads_legacy_target_pane_when_repo_local_target_missing(self) -> None:
        bridge_root = self.temp_dir / "bridge-copy"
        bridge_root.mkdir()
        common_copy = bridge_root / "common.sh"
        common_copy.write_text(
            (REPO_ROOT / "tools" / "tmux_bridge" / "common.sh").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        legacy_target = bridge_root / "target_pane.txt"
        legacy_target.write_text("%42\n", encoding="utf-8")

        result = subprocess.run(
            [
                "bash",
                "-lc",
                (
                    f"set -euo pipefail\n"
                    f"export MACS_REPO_ROOT={shlex.quote(str(self.repo_root))}\n"
                    f"source {shlex.quote(str(common_copy))}\n"
                    f"tmux_bridge_init_state {shlex.quote(str(bridge_root))}\n"
                    f"read_pinned_target_pane\n"
                ),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "%42")
        self.assertFalse((self.repo_root / ".codex" / "target-pane.txt").exists())


if __name__ == "__main__":
    unittest.main()
