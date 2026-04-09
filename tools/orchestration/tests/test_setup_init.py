#!/usr/bin/env python3
"""Tests for orchestration bootstrap and controller lock behavior."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


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

    def test_setup_init_creates_repo_local_layout(self) -> None:
        result = self.run_cli("setup", "init")
        self.assertEqual(result.returncode, 0, result.stderr)

        orchestration_dir = self.repo_root / ".codex" / "orchestration"
        self.assertTrue(orchestration_dir.is_dir())
        self.assertTrue((orchestration_dir / "controller.lock").exists())
        self.assertFalse((orchestration_dir / "state.db").exists())
        self.assertFalse((orchestration_dir / "events.ndjson").exists())

    def test_setup_init_accepts_json_flag_after_subcommand(self) -> None:
        result = self.run_cli("setup", "init", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "macs setup init")
        self.assertIn("controller_lock", payload["data"])

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


if __name__ == "__main__":
    unittest.main()
