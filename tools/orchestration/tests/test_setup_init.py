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

    def init_repo(self) -> None:
        result = self.run_cli("setup", "init")
        self.assertEqual(result.returncode, 0, result.stderr)

    def iso_now(self, *, seconds_ago: int = 0) -> str:
        return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).replace(microsecond=0).isoformat()

    def make_fake_bin(self, *commands: str) -> str:
        bin_dir = self.temp_dir / "bin"
        bin_dir.mkdir(exist_ok=True)
        for command in commands:
            target = bin_dir / command
            if command == "python3":
                target.symlink_to(Path(sys.executable))
                continue
            target.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            target.chmod(0o755)
        return str(bin_dir)

    def seed_worker_row(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        adapter_id: str,
        state: str = "ready",
        capabilities: list[str] | None = None,
        operator_tags: list[str] | None = None,
        tmux_socket: str | None = None,
        tmux_session: str | None = None,
        tmux_pane: str = "%1",
        freshness_seconds: int = 0,
    ) -> None:
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
                    json.dumps(capabilities or [runtime_type]),
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

    def update_governance_policy(self, mutator) -> dict[str, object]:
        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        updated = mutator(governance_policy)
        governance_path.write_text(json.dumps(updated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return updated

    def test_setup_init_bootstraps_review_checkpoint_authority_table_and_bundle_dir(self) -> None:
        self.init_repo()
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        self.assertTrue((orchestration_dir / "checkpoints").is_dir())

        state_db = orchestration_dir / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            row = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'review_checkpoints'
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)

    def start_tmux_worker(self, name: str) -> tuple[str, str, str]:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")
        tmux_dir = self.temp_dir / f"tmux-{name}"
        tmux_dir.mkdir(exist_ok=True)
        socket = tmux_dir / f"{name}.sock"
        session = f"macs-{name}-{os.getpid()}"
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

    def stage_tmux_capture(self, tmux_socket: str, tmux_pane: str, content: str) -> None:
        if not content:
            return
        subprocess.run(
            ["tmux", "-S", tmux_socket, "send-keys", "-t", tmux_pane, "-l", content],
            check=True,
            capture_output=True,
            text=True,
        )

    def seed_interrupted_recovery_run(
        self,
        *,
        task_id: str = "task-startup-interrupted-recovery",
        recovery_run_id: str = "recovery-startup-interrupted-task",
    ) -> tuple[Path, str]:
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        create_task(
            state_db,
            events_ndjson,
            TaskRecord(
                task_id=task_id,
                title="Interrupted restart recovery",
                description="Interrupted restart recovery",
                workflow_class="implementation",
                intent="Interrupted restart recovery",
                required_capabilities=[],
                protected_surfaces=["docs/startup-recovery.md"],
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
                timestamp=self.iso_now(seconds_ago=20),
                actor_type="controller",
                actor_id="controller-main",
                correlation_id=f"corr-task-seed-{task_id}",
                causation_id=None,
                payload={"task_id": task_id},
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
                    self.iso_now(seconds_ago=15),
                    None,
                    json.dumps(
                        {
                            "kind": "ambiguous_ownership",
                            "basis": "worker_state_unavailable",
                            "predecessor_worker_id": "worker-startup-predecessor",
                            "predecessor_lease_id": "lease-startup-predecessor",
                        },
                        sort_keys=True,
                    ),
                    json.dumps(
                        {
                            "allowed_next_actions": [
                                f"macs recovery retry --task {task_id}",
                                f"macs recovery reconcile --task {task_id}",
                            ],
                            "proposed_worker_id": "worker-startup-successor",
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
        return state_db, recovery_run_id

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
        self.assertEqual(payload["data"]["governance_policy"]["status"], "created")
        self.assertTrue(payload["data"]["governance_policy"]["path"].endswith("governance-policy.json"))
        self.assertFalse(payload["data"]["startup_summary"]["assignments_blocked"])

    def test_setup_init_bootstraps_repo_local_governance_policy_file(self) -> None:
        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        governance_path = self.repo_root / ".codex" / "orchestration" / "governance-policy.json"
        self.assertTrue(governance_path.exists())
        governance_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        self.assertEqual(governance_policy["policy_version"], "phase1-governance-v1")
        self.assertIn("audit_content", governance_policy)
        self.assertIn("governed_surfaces", governance_policy)
        self.assertEqual(governance_policy["operating_profile"], "primary_plus_fallback")
        self.assertEqual(governance_policy["surface_version_pins"], [])
        self.assertEqual(governance_policy["secret_scopes"], [])

    def test_surface_version_pin_resolution_returns_explicit_none_configured_when_field_missing(self) -> None:
        from tools.orchestration.policy import resolve_surface_version_pins

        summary = resolve_surface_version_pins(
            {
                "policy_version": "phase1-governance-v1",
                "governed_surfaces": {
                    "allowlisted_surfaces": ["mcp"],
                    "pinned_surfaces": {"mcp": ["codex"]},
                },
                "workflow_surface_overrides": {},
                "audit_content": {},
            },
            workflow_class="implementation",
            operating_profile="primary_plus_fallback",
            adapter_id="codex",
            surface_id="mcp",
        )

        self.assertEqual(summary["state"], "none_configured")
        self.assertEqual(summary["effective_state"], "none_configured")
        self.assertEqual(summary["normalized_pins"], [])
        self.assertEqual(summary["effective_pins"], [])

    def test_secret_scope_resolution_returns_explicit_none_configured_when_field_missing(self) -> None:
        from tools.orchestration.policy import resolve_secret_scopes

        summary = resolve_secret_scopes(
            {
                "policy_version": "phase1-governance-v1",
                "governed_surfaces": {
                    "allowlisted_surfaces": ["mcp"],
                    "pinned_surfaces": {"mcp": ["codex"]},
                },
                "workflow_surface_overrides": {},
                "audit_content": {},
            },
            workflow_class="implementation",
            operating_profile="primary_plus_fallback",
            adapter_id="codex",
            surface_id="mcp",
        )

        self.assertEqual(summary["state"], "none_configured")
        self.assertEqual(summary["effective_state"], "none_configured")
        self.assertEqual(summary["normalized_scopes"], [])
        self.assertEqual(summary["effective_scopes"], [])

    def test_secret_scope_resolution_rejects_inline_secret_material_fields(self) -> None:
        from tools.orchestration.policy import GovernancePolicyValidationError, resolve_secret_scopes

        with self.assertRaisesRegex(
            GovernancePolicyValidationError,
            r"secret_scopes\[0\].*(password|secret_value).*(password|secret_value)",
        ):
            resolve_secret_scopes(
                {
                    "policy_version": "phase1-governance-v1",
                    "operating_profile": "primary_plus_fallback",
                    "governed_surfaces": {
                        "allowlisted_surfaces": ["mcp"],
                        "pinned_surfaces": {"mcp": ["codex"]},
                    },
                    "workflow_surface_overrides": {},
                    "secret_scopes": [
                        {
                            "surface_id": "mcp",
                            "adapter_id": "codex",
                            "workflow_class": "implementation",
                            "operating_profile": "primary_plus_fallback",
                            "secret_ref": "mcp.codex.token",
                            "display_name": "Codex MCP token",
                            "redaction_label": "masked",
                            "secret_value": {"inline_field_present": True},
                            "password": ["drop-this-field"],
                        },
                        {
                            "surface_id": "mcp",
                            "adapter_id": "codex",
                            "workflow_class": "implementation",
                            "operating_profile": "full_hybrid",
                            "secret_ref": "mcp.codex.hybrid",
                            "display_name": "Codex hybrid token",
                            "redaction_label": "masked",
                        },
                    ],
                    "audit_content": {},
                },
                workflow_class="implementation",
                operating_profile="primary_plus_fallback",
                adapter_id="codex",
                surface_id="mcp",
            )

    def test_surface_version_pin_resolution_filters_to_effective_context(self) -> None:
        from tools.orchestration.policy import resolve_surface_version_pins

        summary = resolve_surface_version_pins(
            {
                "policy_version": "phase1-governance-v1",
                "operating_profile": "primary_plus_fallback",
                "governed_surfaces": {
                    "allowlisted_surfaces": ["mcp"],
                    "pinned_surfaces": {"mcp": ["codex"]},
                },
                "workflow_surface_overrides": {},
                "surface_version_pins": [
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
                        "adapter_id": "codex",
                        "workflow_class": "review",
                        "operating_profile": "full_hybrid",
                        "expected_runtime_identity": "codex",
                        "expected_model_identity": "gpt-5.3",
                    },
                ],
                "audit_content": {},
            },
            workflow_class="implementation",
            operating_profile="primary_plus_fallback",
            adapter_id="codex",
            surface_id="mcp",
        )

        self.assertEqual(summary["state"], "configured")
        self.assertEqual(summary["effective_state"], "pins_apply")
        self.assertEqual(len(summary["normalized_pins"]), 2)
        self.assertEqual(len(summary["effective_pins"]), 1)
        self.assertEqual(summary["effective_pins"][0]["expected_model_identity"], "gpt-5.4")

    def test_surface_version_evidence_evaluation_reports_missing_stale_and_untrusted_fail_closed(self) -> None:
        from tools.orchestration.policy import evaluate_surface_version_evidence

        governance_policy = {
            "policy_version": "phase1-governance-v1",
            "operating_profile": "primary_plus_fallback",
            "governed_surfaces": {
                "allowlisted_surfaces": ["mcp"],
                "pinned_surfaces": {},
            },
            "workflow_surface_overrides": {},
            "surface_version_pins": [
                {
                    "surface_id": "mcp",
                    "adapter_id": "local",
                    "workflow_class": "implementation",
                    "operating_profile": "primary_plus_fallback",
                    "expected_runtime_identity": "local",
                    "expected_model_identity": "offline-vetted",
                }
            ],
            "audit_content": {},
        }

        missing_summary = evaluate_surface_version_evidence(
            {
                "worker_id": "worker-missing",
                "runtime_type": "local",
                "adapter_id": "local",
                "freshness_seconds": 5,
            },
            governance_policy,
            workflow_class="implementation",
            surface_ids=["mcp"],
            adapter_evidence=[],
            enforce=True,
        )
        self.assertFalse(missing_summary["eligible"])
        self.assertEqual(missing_summary["blocked_surfaces"][0]["reason"], "surface_version_evidence_missing")

        stale_summary = evaluate_surface_version_evidence(
            {
                "worker_id": "worker-stale",
                "runtime_type": "local",
                "adapter_id": "local",
                "freshness_seconds": 120,
            },
            {
                **governance_policy,
                "surface_version_pins": [
                    {
                        "surface_id": "mcp",
                        "adapter_id": "local",
                        "workflow_class": "implementation",
                        "operating_profile": "primary_plus_fallback",
                        "expected_runtime_identity": "local",
                    }
                ],
            },
            workflow_class="implementation",
            surface_ids=["mcp"],
            adapter_evidence=[
                {
                    "name": "runtime_identity",
                    "confidence": "high",
                    "freshness_seconds": 120,
                    "source_ref": "tmux:test:%1",
                    "value": {"runtime_identity": "local"},
                }
            ],
            enforce=True,
        )
        self.assertFalse(stale_summary["eligible"])
        self.assertEqual(stale_summary["blocked_surfaces"][0]["reason"], "surface_version_evidence_stale")

        untrusted_summary = evaluate_surface_version_evidence(
            {
                "worker_id": "worker-untrusted",
                "runtime_type": "codex",
                "adapter_id": "codex",
                "freshness_seconds": 5,
            },
            {
                **governance_policy,
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
            },
            workflow_class="implementation",
            surface_ids=["mcp"],
            adapter_evidence=[
                {
                    "name": "permission_surface",
                    "confidence": "low",
                    "freshness_seconds": 5,
                    "source_ref": "tmux:test:%1",
                    "value": {"model": "unknown"},
                }
            ],
            enforce=True,
        )
        self.assertFalse(untrusted_summary["eligible"])
        self.assertEqual(untrusted_summary["blocked_surfaces"][0]["reason"], "surface_version_evidence_untrusted")

    def test_surface_version_evidence_evaluation_runtime_only_pins_require_live_runtime_observation(self) -> None:
        from tools.orchestration.policy import evaluate_surface_version_evidence

        summary = evaluate_surface_version_evidence(
            {
                "worker_id": "worker-runtime-only",
                "runtime_type": "codex",
                "adapter_id": "codex",
                "freshness_seconds": 5,
            },
            {
                "policy_version": "phase1-governance-v1",
                "operating_profile": "primary_plus_fallback",
                "governed_surfaces": {"allowlisted_surfaces": ["mcp"], "pinned_surfaces": {}},
                "workflow_surface_overrides": {},
                "surface_version_pins": [
                    {
                        "surface_id": "mcp",
                        "adapter_id": "codex",
                        "workflow_class": "implementation",
                        "operating_profile": "primary_plus_fallback",
                        "expected_runtime_identity": "codex",
                    }
                ],
                "audit_content": {},
            },
            workflow_class="implementation",
            surface_ids=["mcp"],
            adapter_evidence=[
                {
                    "name": "permission_surface",
                    "confidence": "medium",
                    "freshness_seconds": 5,
                    "source_ref": "tmux:test:%1",
                    "value": {"model": "gpt-5.4"},
                }
            ],
            enforce=True,
        )

        self.assertFalse(summary["eligible"])
        self.assertEqual(summary["blocked_surfaces"][0]["reason"], "surface_version_evidence_missing")
        self.assertIsNone(summary["blocked_surfaces"][0]["observed"]["runtime_identity"])

    def test_surface_version_evidence_evaluation_skips_non_matching_context_without_probe(self) -> None:
        from tools.orchestration.policy import evaluate_surface_version_evidence

        summary = evaluate_surface_version_evidence(
            {
                "worker_id": "worker-no-match",
                "runtime_type": "codex",
                "adapter_id": "codex",
                "freshness_seconds": 5,
            },
            {
                "policy_version": "phase1-governance-v1",
                "operating_profile": "primary_plus_fallback",
                "governed_surfaces": {"allowlisted_surfaces": ["mcp"], "pinned_surfaces": {}},
                "workflow_surface_overrides": {},
                "surface_version_pins": [
                    {
                        "surface_id": "mcp",
                        "adapter_id": "codex",
                        "workflow_class": "review",
                        "operating_profile": "primary_plus_fallback",
                        "expected_runtime_identity": "codex",
                        "expected_model_identity": "gpt-5.4",
                    }
                ],
                "audit_content": {},
            },
            workflow_class="implementation",
            surface_ids=["mcp"],
        )

        self.assertTrue(summary["eligible"])
        self.assertFalse(summary["probe_required"])
        self.assertEqual(summary["effective_state"], "no_matching_pins")

    def test_setup_init_bootstraps_separate_config_domain_files(self) -> None:
        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["data"]["controller_defaults"]["status"], "created")
        self.assertEqual(payload["data"]["adapter_settings"]["status"], "created")
        self.assertEqual(payload["data"]["state_layout"]["status"], "created")

        controller_defaults_path = self.repo_root / ".codex" / "orchestration" / "controller-defaults.json"
        adapter_settings_path = self.repo_root / ".codex" / "orchestration" / "adapter-settings.json"
        state_layout_path = self.repo_root / ".codex" / "orchestration" / "state-layout.json"

        self.assertTrue(controller_defaults_path.exists())
        self.assertTrue(adapter_settings_path.exists())
        self.assertTrue(state_layout_path.exists())

        controller_defaults = json.loads(controller_defaults_path.read_text(encoding="utf-8"))
        self.assertEqual(controller_defaults["defaults_version"], "phase1-controller-defaults-v1")
        self.assertEqual(controller_defaults["task"]["default_workflow_class"], "implementation")

        adapter_settings = json.loads(adapter_settings_path.read_text(encoding="utf-8"))
        self.assertEqual(adapter_settings["settings_version"], "phase1-adapter-settings-v1")
        self.assertTrue(adapter_settings["adapters"]["codex"]["enabled"])

        state_layout = json.loads(state_layout_path.read_text(encoding="utf-8"))
        self.assertEqual(state_layout["layout_version"], "phase1-state-layout-v1")
        self.assertEqual(state_layout["paths"]["state_db"], "state.db")
        self.assertIn("tmux_session_file", state_layout["compatibility_paths"])

    def test_setup_check_requires_existing_bootstrap_and_stays_read_only(self) -> None:
        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs setup check")
        self.assertIn("Run 'macs setup init' first", payload["error"]["message"])

        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        self.assertFalse((orchestration_dir / "controller-defaults.json").exists())
        self.assertFalse((orchestration_dir / "adapter-settings.json").exists())
        self.assertFalse((orchestration_dir / "state-layout.json").exists())

    def test_setup_check_reports_config_domains_and_workflow_defaults_in_json(self) -> None:
        self.init_repo()

        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup check")

        configuration = payload["data"]["configuration"]
        self.assertEqual(
            configuration["controller_defaults"]["values"]["task"]["default_workflow_class"],
            "implementation",
        )
        self.assertTrue(configuration["adapter_settings"]["values"]["adapters"]["codex"]["enabled"])
        self.assertIn("implementation", payload["data"]["workflow_defaults"])
        self.assertTrue(payload["data"]["state_paths"]["state_db"].endswith("/state.db"))
        self.assertTrue(
            payload["data"]["compatibility_paths"]["tmux_session_file"].endswith(".codex/tmux-session.txt")
        )
        compatibility = payload["data"]["compatibility"]
        self.assertFalse(compatibility["state_migration_required"])
        self.assertTrue(compatibility["single_worker_mode_supported"])
        self.assertIn("legacy_target_pane_file", compatibility["legacy_metadata"])
        self.assertIn("./tools/tmux_bridge/snapshot.sh", compatibility["supported_unchanged_workflows"]["bridge_helpers"])
        self.assertIn("macs task create --summary <text>", compatibility["superseded_by_control_plane"]["normal_orchestration"])

    def test_setup_check_reports_governance_operating_profile_snapshot_and_no_pins_in_json(self) -> None:
        self.init_repo()

        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance_summary = payload["data"]["configuration"]["governance_policy"]["summary"]
        self.assertEqual(governance_summary["operating_profile"], "primary_plus_fallback")
        self.assertTrue(governance_summary["active_snapshot"]["snapshot_id"].startswith("policy-"))
        self.assertEqual(governance_summary["surface_version_pins"]["state"], "none_configured")
        self.assertEqual(governance_summary["surface_version_pins"]["effective_state"], "none_configured")
        self.assertEqual(governance_summary["surface_version_pins"]["effective_pins"], [])
        self.assertEqual(governance_summary["secret_scopes"]["state"], "none_configured")
        self.assertEqual(governance_summary["secret_scopes"]["effective_state"], "none_configured")
        self.assertEqual(governance_summary["secret_scopes"]["effective_scopes"], [])

    def test_setup_check_reports_effective_surface_version_pins_for_active_profile_in_json(self) -> None:
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
                "adapter_id": "codex",
                "workflow_class": "review",
                "operating_profile": "full_hybrid",
                "expected_runtime_identity": "codex",
                "expected_model_identity": "gpt-5.3",
            },
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance_summary = payload["data"]["configuration"]["governance_policy"]["summary"]
        self.assertEqual(governance_summary["surface_version_pins"]["state"], "configured")
        self.assertEqual(governance_summary["surface_version_pins"]["effective_state"], "pins_apply")
        self.assertEqual(len(governance_summary["surface_version_pins"]["normalized_pins"]), 2)
        self.assertEqual(len(governance_summary["surface_version_pins"]["effective_pins"]), 1)
        self.assertEqual(
            governance_summary["surface_version_pins"]["effective_pins"][0]["expected_model_identity"],
            "gpt-5.4",
        )

    def test_setup_check_reports_effective_secret_scopes_for_active_profile_in_json(self) -> None:
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
                "password": ["drop-this-field"],
            },
            {
                "surface_id": "mcp",
                "adapter_id": "codex",
                "workflow_class": "implementation",
                "operating_profile": "full_hybrid",
                "secret_ref": "mcp.codex.hybrid",
                "display_name": "Codex hybrid token",
                "redaction_label": "masked",
            },
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance_summary = payload["data"]["configuration"]["governance_policy"]["summary"]
        self.assertEqual(governance_summary["secret_scopes"]["state"], "configured")
        self.assertEqual(governance_summary["secret_scopes"]["effective_state"], "scopes_apply")
        self.assertEqual(len(governance_summary["secret_scopes"]["normalized_scopes"]), 2)
        self.assertEqual(len(governance_summary["secret_scopes"]["effective_scopes"]), 1)
        scope = governance_summary["secret_scopes"]["effective_scopes"][0]
        self.assertEqual(scope["secret_ref"], "mcp.codex.token")
        self.assertEqual(scope["display_name"], "Codex MCP token")
        self.assertEqual(scope["redaction_label"], "masked")
        self.assertNotIn("secret_value", scope)
        sanitized_policy = json.loads(governance_path.read_text(encoding="utf-8"))
        self.assertNotIn("secret_value", sanitized_policy["secret_scopes"][0])
        self.assertNotIn("password", sanitized_policy["secret_scopes"][0])

        human_result = self.run_cli("setup", "check")
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("Secret scopes:", human_result.stdout)
        self.assertIn("mcp.codex.token", human_result.stdout)
        self.assertNotIn("secret_value", human_result.stdout)

    def test_setup_check_reports_stale_governance_snapshot_after_post_bootstrap_policy_edit(self) -> None:
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
            }
        ]
        governance_path.write_text(json.dumps(governance_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("setup", "check", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        governance_summary = payload["data"]["configuration"]["governance_policy"]["summary"]
        active_snapshot = governance_summary["active_snapshot"]
        self.assertEqual(active_snapshot["traceability_status"], "stale_vs_live_policy")
        self.assertFalse(active_snapshot["matches_live_policy"])
        self.assertEqual(active_snapshot["surface_version_pins"]["state"], "none_configured")
        self.assertEqual(active_snapshot["surface_version_pins"]["effective_state"], "none_configured")
        self.assertEqual(governance_summary["surface_version_pins"]["effective_state"], "pins_apply")
        self.assertEqual(active_snapshot["secret_scopes"]["state"], "none_configured")
        self.assertEqual(active_snapshot["secret_scopes"]["effective_state"], "none_configured")
        self.assertEqual(governance_summary["secret_scopes"]["effective_state"], "scopes_apply")

        human_result = self.run_cli("setup", "check")
        self.assertEqual(human_result.returncode, 0, human_result.stderr)
        self.assertIn("stale relative to live governance policy", human_result.stdout)
        self.assertIn("Snapshot-captured surface version pins: none configured", human_result.stdout)
        self.assertIn("Snapshot-captured secret scopes: none configured", human_result.stdout)

    def test_setup_check_human_readable_lists_config_domains(self) -> None:
        self.init_repo()

        result = self.run_cli("setup", "check")
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("Configuration domains:", result.stdout)
        self.assertIn("Controller defaults", result.stdout)
        self.assertIn("Adapter settings", result.stdout)
        self.assertIn("Routing policy", result.stdout)
        self.assertIn("Governance policy", result.stdout)
        self.assertIn("State layout", result.stdout)
        self.assertIn("Default workflow class: implementation", result.stdout)
        self.assertIn("Single-worker compatibility:", result.stdout)
        self.assertIn("State migration required: no", result.stdout)
        self.assertIn("Single-worker mode: supported", result.stdout)
        self.assertIn("tools/tmux_bridge/target_pane.txt", result.stdout)
        self.assertIn("Superseded by controller-owned commands:", result.stdout)

    def test_setup_check_human_readable_reports_governance_profile_snapshot_and_no_pins(self) -> None:
        self.init_repo()

        result = self.run_cli("setup", "check")
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("Active operating profile: primary_plus_fallback", result.stdout)
        self.assertIn("Governance snapshot:", result.stdout)
        self.assertIn("Surface version pins: none configured", result.stdout)
        self.assertIn("Secret scopes: none configured", result.stdout)

    def test_setup_validate_blocks_before_bootstrap(self) -> None:
        result = self.run_cli("setup", "validate", "--json")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs setup validate")
        self.assertEqual(payload["error"]["outcome"], "BLOCKED")
        self.assertEqual(payload["error"]["next_action"], "macs setup init")
        self.assertIn("Run 'macs setup init' first", payload["error"]["message"])
        blocked_human = self.run_cli("setup", "validate")
        self.assertEqual(blocked_human.returncode, 2, blocked_human.stdout + blocked_human.stderr)
        self.assertIn("Outcome: BLOCKED", blocked_human.stderr)
        self.assertIn("Next Action: macs setup init", blocked_human.stderr)

    def test_setup_dry_run_is_read_only_and_reports_reference_examples(self) -> None:
        result = self.run_cli("setup", "dry-run", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup dry-run")
        steps = payload["data"]["dry_run"]["steps"]
        self.assertEqual(steps[0]["command"], "macs setup init")
        self.assertIn("macs worker discover --json", payload["data"]["dry_run"]["reference_examples"]["registration"])
        self.assertIn("macs task pause --task <task-id> --confirm", payload["data"]["dry_run"]["reference_examples"]["intervention"][0])
        self.assertIn("macs recovery inspect --task <task-id>", payload["data"]["dry_run"]["reference_examples"]["recovery"][0])
        guidance = payload["data"]["dry_run"]["migration_guidance"]
        self.assertFalse(guidance["state_migration_required"])
        self.assertTrue(guidance["single_worker_mode_supported"])
        self.assertIn("./tools/tmux_bridge/status.sh", guidance["supported_unchanged_workflows"]["bridge_helpers"])
        self.assertIn("macs task inspect --task <task-id>", guidance["superseded_by_control_plane"]["normal_orchestration"])
        self.assertFalse((self.repo_root / ".codex" / "orchestration").exists())

    def test_setup_dry_run_human_readable_lists_conservative_steps(self) -> None:
        result = self.run_cli("setup", "dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("Conservative setup dry-run:", result.stdout)
        self.assertIn("1. macs setup init", result.stdout)
        self.assertIn("5. macs setup validate --json", result.stdout)
        self.assertIn("7. macs recovery inspect --task <task-id>", result.stdout)
        self.assertIn("Single-worker migration:", result.stdout)
        self.assertIn("No repo-local state migration is required.", result.stdout)
        self.assertIn("Legacy metadata:", result.stdout)
        self.assertIn("tools/tmux_bridge/target_pane.txt", result.stdout)

    def test_setup_help_lists_guide_verb(self) -> None:
        result = self.run_cli("setup", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("guide", result.stdout)

    def test_setup_guide_is_read_only_and_succeeds_before_bootstrap(self) -> None:
        result = self.run_cli("setup", "guide", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup guide")

        guide = payload["data"]["guide"]
        self.assertTrue(guide["read_only"])
        self.assertFalse(guide["bootstrap_detected"])
        self.assertEqual(guide["current_phase"], "bootstrap-required")
        self.assertEqual(guide["next_action"]["command"], "macs setup init")
        self.assertEqual(guide["next_action"]["action_type"], "ACTION")
        self.assertIn("macs setup dry-run --json", [item["command"] for item in guide["follow_up_commands"]])
        self.assertFalse((self.repo_root / ".codex" / "orchestration").exists())

    def test_setup_guide_human_readable_labels_commands(self) -> None:
        result = self.run_cli("setup", "guide")
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("Guided setup briefing:", result.stdout)
        self.assertIn("[ACTION] macs setup init", result.stdout)
        self.assertIn("[READ-ONLY] macs setup dry-run --json", result.stdout)

    def test_setup_guide_uses_discover_as_next_action_for_registered_but_not_ready_workers(self) -> None:
        self.init_repo()
        adapter_settings_path = self.repo_root / ".codex" / "orchestration" / "adapter-settings.json"
        settings = json.loads(adapter_settings_path.read_text(encoding="utf-8"))
        settings["adapters"]["claude"]["enabled"] = False
        settings["adapters"]["gemini"]["enabled"] = False
        settings["adapters"]["local"]["enabled"] = False
        adapter_settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.seed_worker_row(
            worker_id="worker-codex-degraded",
            runtime_type="codex",
            adapter_id="codex",
            state="degraded",
        )
        fake_bin = self.make_fake_bin("python3", "tmux", "codex")

        result = self.run_cli(
            "setup",
            "guide",
            "--json",
            env_overrides={"PATH": fake_bin},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        guide = payload["data"]["guide"]
        self.assertTrue(guide["bootstrap_detected"])
        self.assertEqual(guide["current_phase"], "validate-readiness")
        self.assertEqual(guide["current_state"]["outcome"], "PARTIAL")
        self.assertEqual(guide["current_state"]["registered_workers"], 1)
        self.assertEqual(guide["current_state"]["ready_workers"], 0)
        self.assertEqual(guide["next_action"]["command"], "macs worker discover --json")
        self.assertEqual(guide["next_action"]["action_type"], "ACTION")
        self.assertIn("macs setup validate --json", [item["command"] for item in guide["follow_up_commands"]])

    def test_setup_guide_reports_ready_phase_after_bootstrap(self) -> None:
        self.init_repo()
        adapter_settings_path = self.repo_root / ".codex" / "orchestration" / "adapter-settings.json"
        settings = json.loads(adapter_settings_path.read_text(encoding="utf-8"))
        settings["adapters"]["claude"]["enabled"] = False
        settings["adapters"]["gemini"]["enabled"] = False
        adapter_settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.seed_worker_row(worker_id="worker-codex-ready", runtime_type="codex", adapter_id="codex")
        self.seed_worker_row(worker_id="worker-local-ready", runtime_type="local", adapter_id="local")
        fake_bin = self.make_fake_bin("python3", "tmux", "codex")

        result = self.run_cli(
            "setup",
            "guide",
            "--json",
            env_overrides={"PATH": fake_bin},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        guide = payload["data"]["guide"]
        self.assertTrue(guide["bootstrap_detected"])
        self.assertEqual(guide["current_phase"], "ready")
        self.assertEqual(guide["current_state"]["outcome"], "PASS")
        self.assertTrue(guide["current_state"]["safe_ready_state"])
        self.assertEqual(guide["current_state"]["ready_workers"], 2)
        self.assertEqual(guide["next_action"]["command"], "macs setup validate --json")
        self.assertIn("macs setup check --json", [item["command"] for item in guide["follow_up_commands"]])

    def test_setup_validate_reports_partial_outcome_when_bootstrapped_but_not_ready(self) -> None:
        self.init_repo()
        fake_bin = self.make_fake_bin("python3", "tmux")

        result = self.run_cli(
            "setup",
            "validate",
            "--json",
            env_overrides={"PATH": fake_bin},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        validation = payload["data"]["validation"]
        self.assertEqual(validation["outcome"], "PARTIAL")
        self.assertFalse(validation["safe_ready_state_reached"])
        self.assertIn("enabled adapter 'codex' runtime is not available on PATH", validation["gaps"])
        self.assertIn("no ready workers are currently registered", validation["gaps"])

    def test_setup_validate_passes_for_ready_enabled_adapters_in_scope(self) -> None:
        self.init_repo()
        adapter_settings_path = self.repo_root / ".codex" / "orchestration" / "adapter-settings.json"
        settings = json.loads(adapter_settings_path.read_text(encoding="utf-8"))
        settings["adapters"]["claude"]["enabled"] = False
        settings["adapters"]["gemini"]["enabled"] = False
        adapter_settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        self.seed_worker_row(worker_id="worker-codex-ready", runtime_type="codex", adapter_id="codex")
        self.seed_worker_row(worker_id="worker-local-ready", runtime_type="local", adapter_id="local")
        fake_bin = self.make_fake_bin("python3", "tmux", "codex")

        result = self.run_cli(
            "setup",
            "validate",
            "--json",
            env_overrides={"PATH": fake_bin},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        validation = payload["data"]["validation"]
        self.assertEqual(validation["outcome"], "PASS")
        self.assertTrue(validation["safe_ready_state_reached"])
        self.assertEqual(validation["worker_summary"]["ready"], 2)
        self.assertEqual(validation["adapter_summary"]["enabled_adapters"], ["codex", "local"])

    def test_setup_validate_human_readable_reports_outcome_and_gaps(self) -> None:
        self.init_repo()
        fake_bin = self.make_fake_bin("python3", "tmux")

        result = self.run_cli(
            "setup",
            "validate",
            env_overrides={"PATH": fake_bin},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        self.assertIn("Outcome: PARTIAL", result.stdout)
        self.assertIn("Safe Ready State: no", result.stdout)
        self.assertIn("Enabled adapters:", result.stdout)
        self.assertIn("Gaps:", result.stdout)
        self.assertIn("enabled adapter 'codex' runtime is not available on PATH", result.stdout)

    def test_setup_init_uses_custom_state_layout_paths_after_repo_local_edit(self) -> None:
        self.init_repo()

        state_layout_path = self.repo_root / ".codex" / "orchestration" / "state-layout.json"
        state_layout = json.loads(state_layout_path.read_text(encoding="utf-8"))
        state_layout["paths"]["state_db"] = "state/custom-state.db"
        state_layout["paths"]["events_ndjson"] = "audit/custom-events.ndjson"
        state_layout_path.write_text(json.dumps(state_layout, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["data"]["state_db"].endswith("/state/custom-state.db"))
        self.assertTrue(payload["data"]["events_ndjson"].endswith("/audit/custom-events.ndjson"))
        self.assertTrue((self.repo_root / ".codex" / "orchestration" / "state" / "custom-state.db").exists())
        self.assertTrue((self.repo_root / ".codex" / "orchestration" / "audit" / "custom-events.ndjson").exists())

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

    def test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs(self) -> None:
        self.run_cli("setup", "init")
        _, recovery_run_id = self.seed_interrupted_recovery_run()

        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        summary = payload["data"]["startup_summary"]

        self.assertIn("pending_recovery_runs", summary)
        self.assertEqual(len(summary["pending_recovery_runs"]), 1)
        self.assertEqual(summary["pending_recovery_runs"][0]["recovery_run_id"], recovery_run_id)
        self.assertEqual(summary["pending_recovery_runs"][0]["state"], "pending_retry")

    def test_overview_keeps_restart_recovery_tasks_in_reconciliation(self) -> None:
        self.test_restart_marks_live_ownership_for_reconciliation()

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        active_tasks = overview_payload["data"]["overview"]["active_tasks"]

        self.assertEqual(active_tasks[0]["task_id"], "task-006")
        self.assertEqual(active_tasks[0]["state"], "reconciliation")
        self.assertEqual(active_tasks[0]["lease_state"], "suspended")
        self.assertIsNone(active_tasks[0]["next_action"])

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
        )["data"]["result"]["task"]["task_id"]

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
        self.assertEqual(assign_result.returncode, 5)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(payload["errors"][0]["code"], "degraded_precondition")
        self.assertEqual(
            payload["errors"][0]["message"],
            "Assignments are blocked pending startup recovery reconciliation",
        )

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["task"]["current_lease_id"])

    def test_explicit_reroute_can_resolve_startup_recovery_task_while_assignments_blocked(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        self.test_restart_marks_live_ownership_for_reconciliation()

        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        tmux_dir = self.temp_dir / "tmux-reroute"
        tmux_dir.mkdir()
        socket = tmux_dir / "recovery.sock"
        session = f"macs-recovery-{os.getpid()}"
        subprocess.run(
            ["tmux", "-S", str(socket), "new-session", "-d", "-s", session, "-n", "worker"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.addCleanup(
            subprocess.run,
            ["tmux", "-S", str(socket), "kill-server"],
            check=False,
            capture_output=True,
            text=True,
        )
        pane = subprocess.run(
            ["tmux", "-S", str(socket), "list-panes", "-t", session, "-F", "#{pane_id}"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

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
                    "worker-reroute-startup-target",
                    "codex",
                    "codex",
                    str(socket),
                    session,
                    pane,
                    "ready",
                    json.dumps(["implementation"]),
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered"]',
                ),
            )
            conn.commit()
        finally:
            conn.close()

        reroute_result = self.run_cli(
            "task",
            "reroute",
            "--task",
            "task-006",
            "--worker",
            "worker-reroute-startup-target",
            "--confirm",
            "--json",
        )
        self.assertEqual(reroute_result.returncode, 0, reroute_result.stdout + reroute_result.stderr)
        payload = json.loads(reroute_result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["result"]["decision_rights"]["decision_class"], "operator_confirmed")
        self.assertEqual(payload["data"]["result"]["task"]["current_worker_id"], "worker-reroute-startup-target")

        conn = sqlite3.connect(state_db)
        try:
            live_leases = conn.execute(
                """
                SELECT lease_id, state
                FROM leases
                WHERE task_id = ? AND state IN ('active', 'paused', 'suspended', 'expiring')
                ORDER BY lease_id
                """,
                ("task-006",),
            ).fetchall()
            predecessor_row = conn.execute(
                "SELECT state, replacement_lease_id FROM leases WHERE lease_id = ?",
                ("lease-501",),
            ).fetchone()
            recovery_row = conn.execute(
                """
                SELECT state, decision_summary
                FROM recovery_runs
                WHERE task_id = ?
                ORDER BY started_at DESC, recovery_run_id DESC
                LIMIT 1
                """,
                ("task-006",),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(len(live_leases), 1)
        self.assertEqual(predecessor_row[0], "replaced")
        self.assertIsNotNone(predecessor_row[1])
        self.assertEqual(recovery_row[0], "completed")
        self.assertIn("worker-reroute-startup-target", recovery_row[1])

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
        self.assertEqual(inspect_payload["worker"]["adapter_id"], "local")
        self.assertEqual(inspect_payload["worker"]["state"], "ready")

    def test_worker_register_quarantines_surface_version_pin_mismatch_and_records_audit_context(self) -> None:
        self.init_repo()
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
                        "workflow_class": "*",
                        "operating_profile": "primary_plus_fallback",
                        "expected_runtime_identity": "codex",
                        "expected_model_identity": "gpt-5.4",
                    }
                ],
            }
        )
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("register-version-mismatch")
        self.stage_tmux_capture(
            tmux_socket,
            tmux_pane,
            "codex --model gpt-5.4-mini --sandbox workspace-write --yolo",
        )
        self.seed_worker_row(
            worker_id="worker-codex-register-version-mismatch",
            runtime_type="codex",
            adapter_id="local",
            state="registered",
            capabilities=["implementation"],
            operator_tags=["discovered", "surface:mcp"],
            tmux_socket=tmux_socket,
            tmux_session=tmux_session,
            tmux_pane=tmux_pane,
        )

        result = self.run_cli(
            "worker",
            "register",
            "--worker",
            "worker-codex-register-version-mismatch",
            "--adapter",
            "codex",
            "--json",
        )
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertIn("quarantined during registration", payload["error"]["message"])
        self.assertIn("retry registration", payload["error"]["next_action"])
        self.assertEqual(payload["error"]["worker"]["state"], "quarantined")
        blocked = payload["error"]["governance"]["surface_version_pins"]["blocked_surfaces"][0]
        self.assertEqual(blocked["reason"], "surface_version_pin_mismatch")
        self.assertEqual(blocked["observed"]["model_identity"]["identity"], "gpt-5.4-mini")

        state_db = self.repo_root / ".codex" / "orchestration" / "state.db"
        conn = sqlite3.connect(state_db)
        try:
            event_row = conn.execute(
                """
                SELECT event_type, payload
                FROM events
                WHERE aggregate_id = ?
                ORDER BY timestamp DESC, event_id DESC
                LIMIT 1
                """,
                ("worker-codex-register-version-mismatch",),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(event_row)
        self.assertEqual(event_row[0], "worker.quarantined")
        event_payload = json.loads(event_row[1])
        self.assertEqual(event_payload["state"], "quarantined")
        self.assertEqual(
            event_payload["governance"]["surface_version_pins"]["blocked_surfaces"][0]["reason"],
            "surface_version_pin_mismatch",
        )

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
        self.assertEqual(inspect_payload["worker"]["state"], "unavailable")
        self.assertIn("manual_disabled", inspect_payload["worker"]["operator_tags"])

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

    def test_adapter_inspect_exposes_contributor_contract_in_json(self) -> None:
        inspect_result = self.run_cli("adapter", "inspect", "--adapter", "codex", "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        adapter = inspect_payload["data"]["adapter"]
        contract = adapter["contract"]

        self.assertEqual(
            contract["required_operations"],
            [
                "discover_workers",
                "probe",
                "dispatch",
                "capture",
                "interrupt",
                "acknowledge_delivery",
            ],
        )
        self.assertIn("stable_worker_identity", contract["required_facts"])
        self.assertEqual(contract["capability_model"]["declaration_field"], "capabilities")
        self.assertEqual(contract["capability_model"]["evidence_name"], "capability_decl")
        self.assertIn("implementation", contract["capability_model"]["reference_workflow_classes"])
        self.assertIn("runtime_permission_surface", contract["optional_enrichments"]["implemented"])
        self.assertIn("token_budget", contract["optional_enrichments"]["unsupported"])
        self.assertIn("shared_contract_suite", contract["qualification_expectations"])
        self.assertIn("RG1:evidence_based_first_class_qualification", contract["release_gate_criteria"])
        self.assertIn(
            "python3 -m unittest tools.orchestration.tests.test_adapter_contracts",
            contract["validation_commands"],
        )
        self.assertIn(
            "python3 -m unittest tools.orchestration.tests.test_controller_invariants",
            contract["validation_commands"],
        )

    def test_adapter_inspect_human_readable_shows_contributor_guidance(self) -> None:
        inspect_result = self.run_cli("adapter", "inspect", "--adapter", "codex")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)

        self.assertIn("Required Facts:", inspect_result.stdout)
        self.assertIn("Required Operations:", inspect_result.stdout)
        self.assertIn("Capability Model:", inspect_result.stdout)
        self.assertIn("Reference Workflow Classes:", inspect_result.stdout)
        self.assertIn("documentation_context", inspect_result.stdout)
        self.assertIn("Optional Enrichments:", inspect_result.stdout)
        self.assertIn("Degraded Mode:", inspect_result.stdout)
        self.assertIn("Qualification Steps:", inspect_result.stdout)
        self.assertIn("Shared Validation Commands:", inspect_result.stdout)
        self.assertIn("Release-Gate Criteria:", inspect_result.stdout)

    def test_adapter_validate_human_readable_shows_shared_contract_checks(self) -> None:
        validate_result = self.run_cli("adapter", "validate", "--adapter", "codex")
        self.assertEqual(validate_result.returncode, 0, validate_result.stderr)

        self.assertIn("Validation Checks:", validate_result.stdout)
        self.assertIn("required_operations_present: PASS", validate_result.stdout)
        self.assertIn("required_facts_declared: PASS", validate_result.stdout)
        self.assertIn("capability_model_declared: PASS", validate_result.stdout)

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
        self.assertEqual([item["adapter_id"] for item in evidence], ["local", "local", "local", "local"])
        self.assertEqual(
            [item["name"] for item in evidence],
            ["pane_presence", "runtime_identity", "capability_decl", "health_state"],
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
                ["pane_presence", "runtime_identity", "capability_decl", "health_state"],
            )

    def test_task_assign_records_routing_decision_and_locks(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("route")

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
                        tmux_socket,
                        tmux_session,
                        tmux_pane,
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
        task_id = create_payload["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        result = assign_payload["data"]["result"]

        self.assertEqual(result["selected_worker_id"], "worker-codex-route")
        self.assertEqual(result["task"]["state"], "active")
        self.assertEqual(result["task"]["current_worker_id"], "worker-codex-route")
        self.assertIsNotNone(result["task"]["routing_decision"])
        self.assertEqual(result["task"]["routing_decision"]["selected_worker_id"], "worker-codex-route")
        self.assertEqual(len(result["locks"]), 1)
        self.assertEqual(result["locks"][0]["surface_ref"], "backend/api/server.py")
        self.assertEqual(result["locks"][0]["state"], "active")

        inspect_result = self.run_cli("task", "inspect", "--task", task_id, "--json")
        self.assertEqual(inspect_result.returncode, 0, inspect_result.stderr)
        inspect_payload = json.loads(inspect_result.stdout)
        inspected_task = inspect_payload["task"]
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
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("conflict")

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
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
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
        )["data"]["result"]["task"]["task_id"]
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
        )["data"]["result"]["task"]["task_id"]

        second_assign = self.run_cli("task", "assign", "--task", second_task, "--json")
        self.assertEqual(second_assign.returncode, 4)
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
        )["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 4)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(payload["errors"][0]["message"], "No eligible workers for task")

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertEqual(inspect_payload["task"]["state"], "pending_assignment")
        self.assertIsNone(inspect_payload["task"]["current_worker_id"])

    def test_privacy_sensitive_routing_prefers_local_only(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("privacy")

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
                        tmux_socket,
                        tmux_session,
                        tmux_pane,
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
        )["data"]["result"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertEqual(assign_payload["data"]["result"]["selected_worker_id"], "worker-local-privacy")

    def test_privacy_sensitive_routing_reports_local_and_governed_surface_blockers(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"

        seed_event = EventRecord(
            event_id="evt-worker-seed-route-privacy-governed-001",
            event_type="worker.seeded",
            aggregate_type="worker",
            aggregate_id="worker-codex-privacy-governed",
            timestamp="2026-04-09T22:32:00+01:00",
            actor_type="controller",
            actor_id="controller-main",
            correlation_id="corr-worker-seed-route-privacy-governed-001",
            causation_id=None,
            payload={"worker_id": "worker-codex-privacy-governed"},
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
                    "worker-codex-privacy-governed",
                    "codex",
                    "codex",
                    "/tmp/privacy-governed.sock",
                    "privacy-governed",
                    "%9",
                    "ready",
                    '["privacy_sensitive_offline"]',
                    "required_only",
                    self.iso_now(seconds_ago=5),
                    self.iso_now(seconds_ago=5),
                    "interruptible",
                    '["registered","surface:mcp"]',
                ),
            )

        write_eventful_transaction(state_db, events_ndjson, seed_event, mutator)

        task_id = json.loads(
            self.run_cli(
                "task",
                "create",
                "--summary",
                "Privacy governed blockers",
                "--workflow-class",
                "privacy_sensitive_offline",
                "--require-capability",
                "privacy_sensitive_offline",
                "--surface",
                "logical:privacy-governed",
                "--json",
            ).stdout
        )["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 4, assign_result.stdout + assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        rejected = assign_payload["data"]["result"]["routing_evaluation"]["rejected_workers"][0]
        self.assertIn("privacy_sensitive_local_only", rejected["reasons"])
        self.assertIn("governed_surface_not_allowlisted:mcp", rejected["reasons"])

        inspect_payload = json.loads(self.run_cli("task", "inspect", "--task", task_id, "--json").stdout)
        self.assertIn("privacy-sensitive routing rejected non-local workers", inspect_payload["task"]["blocking_condition"])

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
        )["data"]["result"]["task"]["task_id"]

        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 4)
        payload = json.loads(assign_result.stdout)
        self.assertEqual(payload["errors"][0]["message"], "Unsupported workflow class: implementaiton")
        self.assertNotIn("Traceback", assign_result.stderr)

    def test_lease_and_event_inspection_surface_assignment_history(self) -> None:
        self.run_cli("setup", "init")
        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        state_db = orchestration_dir / "state.db"
        events_ndjson = orchestration_dir / "events.ndjson"
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("history")

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
                    tmux_socket,
                    tmux_session,
                    tmux_pane,
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
        )["data"]["result"]["task"]["task_id"]
        assign_payload = json.loads(self.run_cli("task", "assign", "--task", task_id, "--json").stdout)
        lease_id = assign_payload["data"]["result"]["lease_id"]

        lease_inspect = self.run_cli("lease", "inspect", "--lease", lease_id, "--json")
        self.assertEqual(lease_inspect.returncode, 0, lease_inspect.stderr)
        lease_payload = json.loads(lease_inspect.stdout)
        self.assertEqual(lease_payload["data"]["lease"]["task_id"], task_id)
        self.assertEqual(lease_payload["data"]["lease"]["state"], "active")

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
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("overview")

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
                        tmux_socket,
                        tmux_session,
                        tmux_pane,
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
        )["data"]["result"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)

        overview_result = self.run_cli("overview", "show", "--json")
        self.assertEqual(overview_result.returncode, 0, overview_result.stderr)
        overview_payload = json.loads(overview_result.stdout)
        overview = overview_payload["data"]["overview"]

        self.assertEqual(overview["worker_summary"]["ready"], 1)
        self.assertEqual(overview["worker_summary"]["degraded"], 1)
        self.assertEqual(overview["task_summary"]["active"], 1)
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
        tmux_socket, tmux_session, tmux_pane = self.start_tmux_worker("health-route")

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
                        tmux_socket,
                        tmux_session,
                        tmux_pane,
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
        )["data"]["result"]["task"]["task_id"]
        assign_result = self.run_cli("task", "assign", "--task", task_id, "--json")
        self.assertEqual(assign_result.returncode, 0, assign_result.stderr)
        assign_payload = json.loads(assign_result.stdout)
        self.assertEqual(assign_payload["data"]["result"]["selected_worker_id"], "worker-local-fresh")


if __name__ == "__main__":
    unittest.main()
