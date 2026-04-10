#!/usr/bin/env python3
"""Release-gate command coverage for Phase 1 readiness reporting."""

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


REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = [sys.executable, "-m", "tools.orchestration.cli.main"]


class ReleaseGateCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-release-gate-test-"))
        self.repo_root = self.temp_dir / "repo"
        self.repo_root.mkdir()
        self.env = os.environ.copy()
        self.env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + self.env.get("PYTHONPATH", "")
        self.env["TMUX_SESSION"] = "macs-release-gate-test"
        self.env["TMUX_SOCKET"] = "/tmp/macs-release-gate-test.sock"

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

    def seed_worker_row(
        self,
        *,
        worker_id: str,
        runtime_type: str,
        adapter_id: str,
        state: str = "ready",
        capabilities: list[str] | None = None,
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
                    self.env["TMUX_SOCKET"],
                    self.env["TMUX_SESSION"],
                    "%1",
                    state,
                    json.dumps(capabilities or [runtime_type]),
                    "required_only",
                    self.iso_now(),
                    self.iso_now(),
                    "interruptible",
                    json.dumps(["registered"]),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def make_release_gate_path(self) -> str:
        tmux_binary = shutil.which("tmux")
        if tmux_binary is None:
            self.skipTest("tmux not available")
        bin_dir = self.temp_dir / "bin"
        bin_dir.mkdir(exist_ok=True)

        python_link = bin_dir / "python3"
        if not python_link.exists():
            python_link.symlink_to(Path(sys.executable))

        tmux_link = bin_dir / "tmux"
        if not tmux_link.exists():
            tmux_link.symlink_to(Path(tmux_binary))

        for runtime in ("codex", "claude", "gemini"):
            target = bin_dir / runtime
            if target.exists():
                continue
            target.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
            target.chmod(0o755)
        return str(bin_dir)

    def test_release_gate_blocks_before_bootstrap(self) -> None:
        result = self.run_cli("setup", "validate", "--release-gate", "--json")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["command"], "macs setup validate")
        self.assertEqual(payload["error"]["outcome"], "BLOCKED")
        self.assertEqual(payload["error"]["next_action"], "macs setup init")

    def test_release_gate_writes_phase1_evidence_package(self) -> None:
        self.init_repo()
        self.seed_worker_row(worker_id="worker-codex-release", runtime_type="codex", adapter_id="codex")
        self.seed_worker_row(worker_id="worker-claude-release", runtime_type="claude", adapter_id="claude")
        self.seed_worker_row(worker_id="worker-gemini-release", runtime_type="gemini", adapter_id="gemini")
        self.seed_worker_row(worker_id="worker-local-release", runtime_type="local", adapter_id="local")
        fake_path = self.make_release_gate_path()

        result = self.run_cli(
            "setup",
            "validate",
            "--release-gate",
            "--json",
            env_overrides={"PATH": fake_path},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup validate")

        release_gate = payload["data"]["release_gate"]
        self.assertEqual(release_gate["invocation"], "macs setup validate --release-gate")
        self.assertEqual(release_gate["outcome"], "PASS")
        self.assertEqual(
            sorted(release_gate["criteria"]),
            [
                "adapter_qualification",
                "failure_mode_matrix",
                "reference_dogfood",
                "restart_recovery",
                "setup_validation",
            ],
        )
        self.assertEqual(release_gate["criteria"]["adapter_qualification"]["outcome"], "PASS")
        self.assertEqual(release_gate["criteria"]["failure_mode_matrix"]["outcome"], "PASS")
        self.assertEqual(
            release_gate["criteria"]["failure_mode_matrix"]["failure_classes"][0]["failure_class"],
            "worker_disconnect",
        )
        self.assertEqual(
            release_gate["criteria"]["failure_mode_matrix"]["failure_classes"][0]["outcome"],
            "PASS",
        )
        self.assertEqual(release_gate["criteria"]["restart_recovery"]["outcome"], "PASS")
        self.assertEqual(release_gate["criteria"]["reference_dogfood"]["outcome"], "PASS")

        evidence = release_gate["evidence"]
        self.assertTrue(Path(evidence["setup_validation_report"]).exists())
        self.assertTrue(Path(evidence["failure_mode_matrix_report"]).exists())
        self.assertTrue(Path(evidence["restart_recovery_report"]).exists())
        self.assertTrue(Path(evidence["four_worker_dogfood_report"]).exists())
        self.assertTrue(Path(evidence["release_gate_report"]).exists())
        self.assertTrue(Path(evidence["release_gate_summary_json"]).exists())
        self.assertTrue(Path(evidence["adapter_reports"]["codex"]).exists())
        self.assertTrue(Path(evidence["adapter_reports"]["claude"]).exists())
        self.assertTrue(Path(evidence["adapter_reports"]["gemini"]).exists())
        self.assertTrue(Path(evidence["adapter_reports"]["local"]).exists())

    def test_release_gate_human_readable_lists_gate_summary_and_evidence(self) -> None:
        self.init_repo()
        self.seed_worker_row(worker_id="worker-codex-release", runtime_type="codex", adapter_id="codex")
        self.seed_worker_row(worker_id="worker-claude-release", runtime_type="claude", adapter_id="claude")
        self.seed_worker_row(worker_id="worker-gemini-release", runtime_type="gemini", adapter_id="gemini")
        self.seed_worker_row(worker_id="worker-local-release", runtime_type="local", adapter_id="local")
        fake_path = self.make_release_gate_path()

        result = self.run_cli(
            "setup",
            "validate",
            "--release-gate",
            env_overrides={"PATH": fake_path},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Release Gate Outcome: PASS", result.stdout)
        self.assertIn("Invocation: macs setup validate --release-gate", result.stdout)
        self.assertIn("Criteria:", result.stdout)
        self.assertIn("- adapter_qualification: PASS", result.stdout)
        self.assertIn("  - codex: PASS", result.stdout)
        self.assertIn("- failure_mode_matrix: PASS", result.stdout)
        self.assertIn("  - worker_disconnect: PASS", result.stdout)
        self.assertIn("- restart_recovery: PASS", result.stdout)
        self.assertIn("- reference_dogfood: PASS", result.stdout)
        self.assertIn("- release_gate_report:", result.stdout)
        self.assertIn("- release_gate_summary_json:", result.stdout)


if __name__ == "__main__":
    unittest.main()
