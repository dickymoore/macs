#!/usr/bin/env python3
"""Deterministic contract tests for shared runtime adapter behavior."""

from __future__ import annotations

import unittest
from unittest import mock

from tools.orchestration.adapters.base import BaseTmuxAdapter
from tools.orchestration.adapters.codex import CodexAdapter
from tools.orchestration.adapters.registry import build_adapter_registry


class AdapterContractTests(unittest.TestCase):
    def test_shared_validation_commands_include_dedicated_contract_and_invariant_suites(self) -> None:
        adapter = CodexAdapter()
        validation = adapter.validate_contract()

        self.assertIn(
            "python3 -m unittest tools.orchestration.tests.test_adapter_contracts",
            validation["validation_commands"],
        )
        self.assertIn(
            "python3 -m unittest tools.orchestration.tests.test_controller_invariants",
            validation["validation_commands"],
        )

    def test_reference_adapter_cannot_qualify_as_first_class_when_contract_fails(self) -> None:
        broken = BaseTmuxAdapter(
            adapter_id="broken-ref",
            runtime_type="broken",
            degraded_mode="",
            unsupported_features=["token_budget"],
            qualification_status="reference",
        )

        validation = broken.validate_contract()
        gate = broken.qualification_gate(validation)

        self.assertFalse(validation["ok"])
        self.assertFalse(gate["shared_contract_passed"])
        self.assertTrue(gate["declared_first_class_candidate"])
        self.assertFalse(gate["first_class_eligible"])
        self.assertIn("shared_contract_failed", gate["blocked_reasons"])

    def test_registry_adapters_pass_shared_contract_suite(self) -> None:
        registry = build_adapter_registry()

        for adapter_id, adapter in registry.items():
            with self.subTest(adapter=adapter_id):
                descriptor = adapter.descriptor()
                validation = adapter.validate_contract()
                self.assertTrue(validation["ok"])
                self.assertTrue(validation["required_operations_present"])
                self.assertTrue(validation["required_facts_declared"])
                self.assertTrue(validation["unsupported_features_declared"])
                self.assertTrue(validation["degraded_mode_declared"])
                self.assertGreaterEqual(len(validation["unsupported_features"]), 1)
                self.assertTrue(descriptor["degraded_mode_behavior"])

    def test_codex_probe_normalizes_permission_surface_claim(self) -> None:
        adapter = CodexAdapter()
        worker = {
            "worker_id": "worker-codex-contract",
            "tmux_socket": "/tmp/contract.sock",
            "tmux_session": "contract",
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
            return_value={
                "ok": True,
                "adapter_id": "codex",
                "worker_id": "worker-codex-contract",
                "output": 'codex --model gpt-5.4 --sandbox workspace-write --yolo\n',
            },
        ):
            evidence = adapter.probe(worker)

        permission_surface = evidence[-1]
        self.assertEqual(permission_surface["kind"], "claim")
        self.assertEqual(permission_surface["name"], "permission_surface")
        self.assertEqual(permission_surface["value"]["model"], "gpt-5.4")
        self.assertEqual(permission_surface["value"]["sandbox"], "workspace-write")
        self.assertEqual(permission_surface["value"]["approval_policy"], "yolo")


if __name__ == "__main__":
    unittest.main()
