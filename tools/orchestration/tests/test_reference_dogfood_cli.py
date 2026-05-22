#!/usr/bin/env python3
"""tmux-backed reference dogfood coverage for the four-worker release scenario."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.orchestration.dogfood import run_reference_dogfood


REPO_ROOT = Path(__file__).resolve().parents[3]


class ReferenceDogfoodCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="macs-dogfood-reference-test-"))
        self.repo_root = self.temp_dir / "repo"
        self.repo_root.mkdir()
        self.report_path = self.temp_dir / "release-evidence" / "four-worker-dogfood-report.md"
        self.artifacts_dir = self.temp_dir / "release-evidence" / "four-worker-dogfood-artifacts"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_reference_dogfood_run_covers_all_four_workers_and_writes_evidence(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        result = run_reference_dogfood(
            self.repo_root,
            report_path=self.report_path,
            artifacts_dir=self.artifacts_dir,
            operator_id="qa.dogfood@example.test",
            scenario_label="unit-test",
        )

        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(
            sorted(worker["runtime"] for worker in result["worker_lineup"]),
            ["claude", "codex", "gemini", "local"],
        )
        self.assertTrue(result["controller_facts"]["ownership_remained_explicit"])
        self.assertTrue(result["controller_facts"]["lock_state_remained_inspectable"])
        self.assertTrue(result["controller_facts"]["event_history_remained_inspectable"])
        self.assertTrue(result["controller_facts"]["zero_or_one_live_lease_held"])

        timing = result["timing_envelope"]
        self.assertEqual(timing["worker_discovery_or_inspection"]["result"], "PASS")
        self.assertEqual(timing["task_assignment_path"]["result"], "PASS")
        self.assertEqual(timing["degraded_warning_visibility"]["result"], "PASS")
        self.assertLessEqual(timing["worker_discovery_or_inspection"]["actual_seconds"], 2.0)
        self.assertLessEqual(timing["task_assignment_path"]["actual_seconds"], 5.0)
        self.assertLessEqual(timing["degraded_warning_visibility"]["actual_seconds"], 10.0)

        intervention = result["intervention"]
        self.assertEqual(intervention["action"], "pause_resume")
        self.assertTrue(intervention["supported"])
        self.assertTrue(intervention["decision_event_id"])
        self.assertTrue(intervention["state_change_event_id"])

        self.assertTrue(self.report_path.exists())
        self.assertTrue((self.artifacts_dir / "four-worker-dogfood-summary.json").exists())
        self.assertTrue((self.artifacts_dir / "four-worker-dogfood-pane-captures.json").exists())

    def test_reference_dogfood_report_uses_template_sections_and_records_controlled_warning_note(self) -> None:
        if shutil.which("tmux") is None:
            self.skipTest("tmux not available")

        run_reference_dogfood(
            self.repo_root,
            report_path=self.report_path,
            artifacts_dir=self.artifacts_dir,
            operator_id="qa.dogfood@example.test",
            scenario_label="unit-test",
        )

        report_text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("# Four-Worker Dogfood Report", report_text)
        self.assertIn("## 1. Run Metadata", report_text)
        self.assertIn("## 4. Reference Timing Envelope", report_text)
        self.assertIn("## 7. Story Acceptance Check", report_text)
        self.assertIn("controlled stale-evidence injection", report_text)
        self.assertIn("Dogfood run counts toward release gate: yes", report_text)

        summary = json.loads((self.artifacts_dir / "four-worker-dogfood-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["outcome"], "PASS")
        self.assertEqual(summary["run_metadata"]["operator"], "qa.dogfood@example.test")
        self.assertEqual(summary["warning_visibility"]["trigger"], "controlled_stale_evidence")
        self.assertTrue(summary["artifact_inventory"]["event_ids"])


if __name__ == "__main__":
    unittest.main()
