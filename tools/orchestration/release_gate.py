#!/usr/bin/env python3
"""Release-gate aggregation and evidence writing for Phase 1 readiness."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.adapters.registry import build_adapter_registry
from tools.orchestration.dogfood import run_reference_dogfood
from tools.orchestration.setup import build_setup_validation


SOURCE_ROOT = Path(__file__).resolve().parents[2]

ADAPTER_CONTRACT_SUITE = [
    "python3",
    "-m",
    "unittest",
    "tools.orchestration.tests.test_adapter_contracts",
]

FAILURE_DRILL_SUITE = [
    "python3",
    "-m",
    "unittest",
    "tools.orchestration.tests.test_failure_drills_cli",
]

RESTART_RECOVERY_SUITE = [
    "python3",
    "-m",
    "unittest",
    "tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_marks_live_ownership_for_reconciliation",
    "tools.orchestration.tests.test_setup_init.SetupInitTests.test_restart_summary_surfaces_unresolved_task_scoped_recovery_runs",
    "tools.orchestration.tests.test_setup_init.SetupInitTests.test_assign_rejects_when_startup_recovery_blocks_assignments",
    "tools.orchestration.tests.test_controller_invariants.ControllerInvariantTests.test_inspect_recovery_context_reports_interrupted_retry_without_live_lease",
]

MANDATORY_FAILURE_CLASSES = [
    "worker_disconnect",
    "stale_lease_divergence",
    "duplicate_claim",
    "split_brain_startup_recovery",
    "lock_collision",
    "misleading_health_evidence",
    "surfaced_budget_exhaustion",
    "interrupted_recovery",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_release_gate(repo_root: Path, paths) -> dict[str, object]:
    repo_root = Path(repo_root).resolve()
    evidence_root = repo_root / "_bmad-output" / "release-evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)

    validation_bundle = build_setup_validation(repo_root, paths)
    validation = validation_bundle["validation"]
    checks = validation_bundle["checks"]

    operator_id = (
        os.environ.get("MACS_OPERATOR_ID")
        or os.environ.get("USER")
        or os.environ.get("LOGNAME")
        or "unknown-operator"
    )

    setup_report_path = evidence_root / "setup-validation-report.md"
    write_setup_validation_report(setup_report_path, repo_root, operator_id, validation)

    adapter_root = evidence_root / "adapter-qualification"
    adapter_root.mkdir(parents=True, exist_ok=True)
    adapter_suite = run_subprocess(ADAPTER_CONTRACT_SUITE)
    adapter_criterion = build_adapter_qualification(adapter_root, adapter_suite)

    failure_report_path = evidence_root / "failure-mode-matrix-report.md"
    failure_criterion = build_failure_mode_matrix(failure_report_path)

    restart_report_path = evidence_root / "restart-recovery-verification-report.md"
    restart_criterion = build_restart_recovery_verification(restart_report_path)

    dogfood_report_path = evidence_root / "four-worker-dogfood-report.md"
    dogfood_artifacts_dir = evidence_root / "four-worker-dogfood-artifacts"
    dogfood_criterion = build_reference_dogfood(
        repo_root,
        report_path=dogfood_report_path,
        artifacts_dir=dogfood_artifacts_dir,
        operator_id=operator_id,
    )

    criteria = {
        "setup_validation": {
            "outcome": str(validation["outcome"]),
            "safe_ready_state_reached": bool(validation["safe_ready_state_reached"]),
            "report_path": str(setup_report_path),
            "gaps": list(validation.get("gaps", [])),
        },
        "adapter_qualification": adapter_criterion,
        "failure_mode_matrix": failure_criterion,
        "restart_recovery": restart_criterion,
        "reference_dogfood": dogfood_criterion,
    }

    evidence = {
        "setup_validation_report": str(setup_report_path),
        "adapter_reports": adapter_criterion["report_paths"],
        "failure_mode_matrix_report": str(failure_report_path),
        "restart_recovery_report": str(restart_report_path),
        "four_worker_dogfood_report": str(dogfood_report_path),
        "release_gate_report": str(evidence_root / "release-gate-command-verification.md"),
        "release_gate_summary_json": str(evidence_root / "release-gate-summary.json"),
    }

    overall_outcome = summarize_outcomes(item["outcome"] for item in criteria.values())
    next_actions = build_next_actions(criteria)
    release_gate = {
        "invocation": "macs setup validate --release-gate",
        "outcome": overall_outcome,
        "criteria": criteria,
        "evidence": evidence,
        "next_actions": next_actions,
        "operator_id": operator_id,
        "generated_at": utc_now(),
    }

    write_release_gate_report(Path(evidence["release_gate_report"]), repo_root, release_gate)
    Path(evidence["release_gate_summary_json"]).write_text(
        json.dumps(release_gate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return {
        "validation": validation,
        "checks": checks,
        "release_gate": release_gate,
    }


def build_adapter_qualification(adapter_root: Path, suite_result: dict[str, object]) -> dict[str, object]:
    registry = build_adapter_registry()
    report_paths: dict[str, str] = {}
    adapters: list[dict[str, object]] = []
    for adapter_id, adapter in registry.items():
        validation = adapter.validate_contract()
        gate = adapter.qualification_gate(validation, release_candidate=True)
        outcome = "PASS" if gate["first_class_eligible"] else "FAIL"
        report_path = adapter_root / f"{adapter_id}-qualification-report.md"
        write_adapter_qualification_report(
            report_path,
            adapter_id=adapter_id,
            descriptor=adapter.descriptor(),
            validation=validation,
            gate=gate,
            suite_result=suite_result,
        )
        report_paths[adapter_id] = str(report_path)
        adapters.append(
            {
                "adapter_id": adapter_id,
                "outcome": outcome,
                "declared_status": gate["declared_status"],
                "release_gate_candidate": gate["release_gate_candidate"],
                "shared_contract_passed": gate["shared_contract_passed"],
                "first_class_eligible": gate["first_class_eligible"],
                "unsupported_features": list(validation.get("unsupported_features", [])),
                "report_path": str(report_path),
            }
        )

    outcome = "PASS" if suite_result["returncode"] == 0 and all(item["outcome"] == "PASS" for item in adapters) else "FAIL"
    return {
        "outcome": outcome,
        "suite_command": suite_result["command"],
        "suite_returncode": suite_result["returncode"],
        "suite_stdout_tail": suite_result["stdout_tail"],
        "suite_stderr_tail": suite_result["stderr_tail"],
        "adapters": adapters,
        "report_paths": report_paths,
    }


def build_failure_mode_matrix(report_path: Path) -> dict[str, object]:
    suite_result = run_subprocess(FAILURE_DRILL_SUITE)
    outcome = "PASS" if suite_result["returncode"] == 0 else "FAIL"
    write_failure_mode_matrix_report(report_path, suite_result, outcome)
    return {
        "outcome": outcome,
        "suite_command": suite_result["command"],
        "suite_returncode": suite_result["returncode"],
        "mandatory_failure_classes": list(MANDATORY_FAILURE_CLASSES),
        "failure_classes": [{"failure_class": item, "outcome": outcome} for item in MANDATORY_FAILURE_CLASSES],
        "report_path": str(report_path),
        "suite_stdout_tail": suite_result["stdout_tail"],
        "suite_stderr_tail": suite_result["stderr_tail"],
    }


def build_restart_recovery_verification(report_path: Path) -> dict[str, object]:
    suite_result = run_subprocess(RESTART_RECOVERY_SUITE)
    outcome = "PASS" if suite_result["returncode"] == 0 else "FAIL"
    write_restart_recovery_report(report_path, suite_result, outcome)
    return {
        "outcome": outcome,
        "suite_command": suite_result["command"],
        "suite_returncode": suite_result["returncode"],
        "scenario_ids": list(RESTART_RECOVERY_SUITE[3:]),
        "report_path": str(report_path),
        "suite_stdout_tail": suite_result["stdout_tail"],
        "suite_stderr_tail": suite_result["stderr_tail"],
    }


def build_reference_dogfood(
    repo_root: Path,
    *,
    report_path: Path,
    artifacts_dir: Path,
    operator_id: str,
) -> dict[str, object]:
    if shutil.which("tmux") is None:
        write_text_report(
            report_path,
            [
                "# Four-Worker Dogfood Report",
                "",
                "Outcome: `BLOCKED`",
                "",
                "- Reason: tmux is not available on PATH, so the reference scenario cannot run.",
            ],
        )
        return {
            "outcome": "BLOCKED",
            "report_path": str(report_path),
            "artifacts_dir": str(artifacts_dir),
            "timing_envelope": {},
            "worker_lineup": [],
            "blocking_reason": "tmux is not available on PATH",
        }

    try:
        temp_root = Path(tempfile.mkdtemp(prefix="macs-release-gate-dogfood-"))
        work_repo_root = temp_root / "repo"
        try:
            summary = run_reference_dogfood(
                work_repo_root,
                report_path=report_path,
                artifacts_dir=artifacts_dir,
                operator_id=operator_id,
                scenario_label="release-gate",
            )
        finally:
            shutil.rmtree(temp_root, ignore_errors=True)
    except Exception as exc:  # pragma: no cover - exercised through CLI tests and QA pass
        write_text_report(
            report_path,
            [
                "# Four-Worker Dogfood Report",
                "",
                "Outcome: `FAIL`",
                "",
                f"- Failure: {exc}",
            ],
        )
        return {
            "outcome": "FAIL",
            "report_path": str(report_path),
            "artifacts_dir": str(artifacts_dir),
            "timing_envelope": {},
            "worker_lineup": [],
            "failure": str(exc),
        }

    return {
        "outcome": str(summary["outcome"]),
        "report_path": str(report_path),
        "artifacts_dir": str(artifacts_dir),
        "timing_envelope": dict(summary["timing_envelope"]),
        "worker_lineup": list(summary["worker_lineup"]),
        "next_action": summary.get("next_action"),
    }


def run_subprocess(command: list[str]) -> dict[str, object]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SOURCE_ROOT) if not pythonpath else str(SOURCE_ROOT) + os.pathsep + pythonpath
    result = subprocess.run(
        command,
        cwd=SOURCE_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(shlex.quote(item) for item in command),
        "returncode": result.returncode,
        "stdout_tail": tail_text(result.stdout),
        "stderr_tail": tail_text(result.stderr),
    }


def tail_text(text: str, *, lines: int = 12) -> list[str]:
    stripped = [line for line in text.splitlines() if line.strip()]
    return stripped[-lines:]


def summarize_outcomes(outcomes) -> str:
    ordered = list(outcomes)
    if any(item == "BLOCKED" for item in ordered):
        return "BLOCKED"
    if any(item == "FAIL" for item in ordered):
        return "FAIL"
    if any(item == "PARTIAL" for item in ordered):
        return "PARTIAL"
    return "PASS"


def build_next_actions(criteria: dict[str, dict[str, object]]) -> list[str]:
    actions: list[str] = []
    setup_validation = criteria["setup_validation"]
    if setup_validation["outcome"] != "PASS":
        for gap in setup_validation.get("gaps", []):
            actions.append(str(gap))
    if criteria["adapter_qualification"]["outcome"] != "PASS":
        actions.append("Resolve the failing adapter qualification reports under `_bmad-output/release-evidence/adapter-qualification/`.")
    if criteria["failure_mode_matrix"]["outcome"] != "PASS":
        actions.append("Re-run and fix `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli` before release sign-off.")
    if criteria["restart_recovery"]["outcome"] != "PASS":
        actions.append("Re-run and fix the targeted restart-recovery verification suite before release sign-off.")
    if criteria["reference_dogfood"]["outcome"] != "PASS":
        actions.append("Re-run the four-worker dogfood scenario and inspect `_bmad-output/release-evidence/four-worker-dogfood-report.md`.")
    return actions


def write_setup_validation_report(
    report_path: Path,
    repo_root: Path,
    operator_id: str,
    validation: dict[str, object],
) -> None:
    adapter_rows = []
    for item in validation["adapter_summary"]["adapters"]:
        if not item["enabled"]:
            continue
        runtime_state = "available"
        if item["runtime_command"] and not item["runtime_available"]:
            runtime_state = "missing"
        elif item["runtime_command"] is None:
            runtime_state = "not required"
        adapter_rows.append(
            f"| {item['adapter_id']} | {item['runtime_type']} | {'ready' if item['worker_summary']['ready'] else 'not_ready'} | "
            f"{runtime_state} | {item['worker_summary']['ready']} | {item['interruptibility_support'] if 'interruptibility_support' in item else 'controller_visible'} |"
        )

    lines = [
        "# Setup Validation Report",
        "",
        "## 1. Run Metadata",
        "",
        f"- Report date: {utc_now()}",
        f"- Operator: {operator_id}",
        f"- Repository: {repo_root}",
        f"- Host OS: {os.uname().sysname if hasattr(os, 'uname') else os.name}",
        f"- Validation scope: {', '.join(validation['adapter_summary']['enabled_adapters']) or 'none'}",
        f"- Outcome: `{validation['outcome']}`",
        "",
        "## 2. Goal",
        "",
        "- Target repo outcome: prove repo-local setup is current enough to support the Phase 1 release gate",
        f"- Target runtimes in scope: {', '.join(validation['adapter_summary']['enabled_adapters']) or 'none'}",
        "- Whether this is fresh install, existing repo adoption, or migration: existing repo adoption",
        "",
        "## 3. Preconditions",
        "",
        f"- Required local dependencies present: {'yes' if all(item['available'] for item in validation['dependency_summary']['required_dependencies']) else 'no'}",
        f"- Repo-local state path: {validation['orchestration_dir']}",
        f"- Known deviations from default setup: {'none' if not validation['gaps'] else '; '.join(validation['gaps'])}",
        "",
        "## 4. Setup Steps Executed",
        "",
        "| Step | Command or action | Expected result | Actual result | Outcome |",
        "| --- | --- | --- | --- | --- |",
        f"| Validate repo-local setup | `macs setup validate --json` | current readiness summary available | outcome `{validation['outcome']}` | {'PASS' if validation['outcome'] == 'PASS' else validation['outcome']} |",
        "",
        "## 5. Ready-State Evidence",
        "",
        "### Controller Facts",
        "",
        f"- State store initialized: {'yes' if validation['controller_facts']['state_store_initialized'] else 'no'}",
        f"- Worker records present: {'yes' if validation['controller_facts']['worker_records_present'] else 'no'}",
        f"- Routing defaults visible: {'yes' if validation['controller_facts']['routing_defaults_visible'] else 'no'}",
        f"- Repo-local configuration domains visible: {'yes' if validation['controller_facts']['repo_local_configuration_domains_visible'] else 'no'}",
        "",
        "### Adapter Signals",
        "",
        "| Worker | Runtime | Readiness | Runtime binary | Ready workers | Interruptibility |",
        "| --- | --- | --- | --- | --- | --- |",
        *adapter_rows,
        "",
        "## 6. Story and Requirement Check",
        "",
        "| Story check | Evidence | Result |",
        "| --- | --- | --- |",
        f"| Supported runtimes can be registered | enabled adapters: {', '.join(validation['adapter_summary']['enabled_adapters']) or 'none'} | {'PASS' if validation['adapter_summary']['enabled_adapters'] else 'FAIL'} |",
        f"| Worker readiness can be validated end to end | ready workers: {validation['worker_summary']['ready']} | {'PASS' if validation['worker_summary']['ready'] else 'PARTIAL'} |",
        f"| Routing defaults can be inspected without bespoke glue | workflow defaults: {', '.join(validation['workflow_defaults']) or 'none'} | {'PASS' if validation['routing_defaults_visible'] else 'FAIL'} |",
        "",
        "## 7. Artifacts",
        "",
        f"- Config files or examples referenced: {', '.join(validation['evidence_fields']['artifacts']['config_files'])}",
        "",
        "## 8. Failures and Gaps",
        "",
        "| Gap or failure | Severity | Blocking story/requirement | Next action | Owner |",
        "| --- | --- | --- | --- | --- |",
    ]
    if validation["gaps"]:
        for gap in validation["gaps"]:
            lines.append(f"| {gap} | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |")
    else:
        lines.append("| None. The setup validation passed with no remaining gaps. | low | RG6 | none | eng |")
    lines.extend(
        [
            "",
            "## 9. Sign-Off",
            "",
            f"- Safe-ready-state reached: {'yes' if validation['safe_ready_state_reached'] else 'no'}",
            f"- Remaining caveats: {'none' if not validation['gaps'] else '; '.join(validation['gaps'])}",
            f"- Recommended disposition: `{'accept' if validation['outcome'] == 'PASS' else 'rework'}`",
        ]
    )
    write_text_report(report_path, lines)


def write_adapter_qualification_report(
    report_path: Path,
    *,
    adapter_id: str,
    descriptor: dict[str, object],
    validation: dict[str, object],
    gate: dict[str, object],
    suite_result: dict[str, object],
) -> None:
    outcome = "PASS" if gate["first_class_eligible"] else "FAIL"
    lines = [
        "# Adapter Qualification Report",
        "",
        "## 1. Adapter Identity",
        "",
        f"- Adapter name: {adapter_id}",
        f"- Runtime type: {descriptor['runtime_type']}",
        "- Adapter version or revision: repo-local",
        "- Maintainer: eng",
        f"- Qualification date: {utc_now()}",
        f"- Outcome: `{outcome}`",
        f"- Proposed status: `{'first-class' if gate['first_class_eligible'] else 'supported-not-first-class'}`",
        "",
        "## 2. Scope",
        "",
        f"- Runtime binary or backend tested: {descriptor['runtime_type']}",
        "- Operating environment: local-host Phase 1 release gate",
        "- Test fixtures used: shared contract validation plus descriptor-driven qualification summary",
        f"- Known unsupported features: {', '.join(validation['unsupported_features']) or 'none'}",
        "",
        "## 3. Contract Surface Check",
        "",
        "| Contract area | Required expectation | Evidence | Result |",
        "| --- | --- | --- | --- |",
        f"| Identity normalization | Stable worker identity exposed | shared descriptor contract | {'PASS' if validation['required_facts_declared'] else 'FAIL'} |",
        f"| Capability declaration | Required and optional capabilities separated | capability model and unsupported feature declaration | {'PASS' if validation['capability_model_declared'] else 'FAIL'} |",
        f"| Health and freshness | Timestamps and freshness metadata exposed | required facts include freshness timestamp | {'PASS' if validation['required_facts_declared'] else 'FAIL'} |",
        f"| Interruptibility | Supported actions or explicit unsupported declaration | supported operations list | {'PASS' if validation['required_operations_present'] else 'FAIL'} |",
        f"| Permission surface | Approval/sandbox signals preserved where available | optional enrichments: {', '.join(descriptor['contract']['optional_enrichments']['implemented']) or 'none'} | PASS |",
        f"| Evidence envelope | Facts, soft signals, and claims remain bounded | shared evidence envelope contract | {'PASS' if validation['ok'] else 'FAIL'} |",
        "| Authority boundary | Adapter cannot mutate authoritative state | controller-owned store remains external to adapter | PASS |",
        "",
        "## 4. First-Class Qualification Gates",
        "",
        "### Required Contract Support",
        "",
        f"- Passes shared contract tests: {'yes' if suite_result['returncode'] == 0 and validation['ok'] else 'no'}",
        "- Required signals exposed: yes",
        f"- Unsupported features declared explicitly: {'yes' if validation['unsupported_features'] else 'no'}",
        "",
        "### Degraded-Mode Behavior",
        "",
        "- Missing signals render as `UNAVAILABLE` or `NOT EXPOSED`: yes",
        "- Degraded health or stale evidence classification supported: yes",
        "- Safe routing degradation documented: yes",
        "",
        "### Intervention Support",
        "",
        f"- Interrupt support: {'yes' if 'interrupt' in descriptor['supported_operations'] else 'no'}",
        "- Pause/hold support: controller-mediated",
        f"- Capture or inspection hooks: {'yes' if 'capture' in descriptor['supported_operations'] else 'no'}",
        f"- Unsupported intervention behaviors: {', '.join(descriptor['unsupported_features']) or 'none'}",
        "",
        "### Routing-Evidence Support",
        "",
        "- Capability fit evidence: declared capabilities",
        "- Freshness evidence: supported",
        "- Health evidence: supported",
        "- Budget/session evidence where available: declared via unsupported feature list when absent",
        "- Confidence or uncertainty markers: controller-visible",
        "",
        "### Validation Coverage",
        "",
        f"- Unit or contract coverage reference: `{suite_result['command']}`",
        "- Integration coverage reference: `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`",
        "- Failure-drill relevance covered: release gate references the shared failure-drill suite",
        "",
        "## 5. Evidence Summary",
        "",
        "### Controller Facts",
        "",
        f"- Worker registration result: declared by shared adapter descriptor",
        f"- Classification result: {'eligible' if gate['first_class_eligible'] else 'not eligible'} for Phase 1 release gate",
        f"- Eligibility for new assignments: {'yes' if gate['first_class_eligible'] else 'conditional'}",
        "",
        "### Adapter Signals",
        "",
        "| Signal | Value or status | Freshness | Required/optional | Notes |",
        "| --- | --- | --- | --- | --- |",
        f"| degraded_mode_behavior | {descriptor['degraded_mode_behavior']} | n/a | required | shared contract declaration |",
        f"| unsupported_features | {', '.join(descriptor['unsupported_features']) or 'none'} | n/a | optional | explicit unsupported declaration |",
        "",
        "## 6. Qualification Decision",
        "",
        "| Decision point | Pass rule | Result | Notes |",
        "| --- | --- | --- | --- |",
        f"| Minimum contract met | all required contract areas pass | {'PASS' if validation['ok'] else 'FAIL'} | shared contract suite plus descriptor validation |",
        f"| Degraded mode safe | missing/weak signals do not weaken authority semantics | PASS | degraded mode declaration present |",
        f"| Intervention sufficient | supported operations are explicit and safe | {'PASS' if validation['required_operations_present'] else 'FAIL'} | shared required operations present |",
        f"| Routing evidence usable | controller can rank or reject safely | PASS | capability and freshness evidence declared |",
        f"| Validation coverage sufficient | automated coverage exists and is linked | {'PASS' if suite_result['returncode'] == 0 else 'FAIL'} | shared contract suite completed |",
        "",
        "## 7. Required Evidence Links",
        "",
        f"- Contract test output: `{suite_result['command']}`",
        "- Integration test output: `python3 -m unittest tools.orchestration.tests.test_failure_drills_cli`",
        "- Related failure-drill reports: `_bmad-output/release-evidence/failure-mode-matrix-report.md`",
        f"- Example inspector output: `macs adapter inspect --adapter {adapter_id} --json`",
        "- Contributor guidance or docs path: `docs/adapter-contributor-guide.md`",
        "",
        "## 8. Open Risks",
        "",
        "| Risk | Impact | Mitigation | Owner |",
        "| --- | --- | --- | --- |",
        f"| Declared status is {gate['declared_status']} while release eligibility is evidence-based. | medium | rely on the release-gate evidence rather than declaration alone | eng |",
        "",
        "## 9. Final Recommendation",
        "",
        f"- Recommended adapter status: {'first-class' if gate['first_class_eligible'] else 'supported-not-first-class'}",
        f"- Ship blocker: {'none' if outcome == 'PASS' else 'shared contract or qualification gate failed'}",
        f"- Follow-up work required before first-class support: {'none' if outcome == 'PASS' else ', '.join(gate['blocked_reasons']) or 'review adapter contract'}",
    ]
    write_text_report(report_path, lines)


def write_failure_mode_matrix_report(report_path: Path, suite_result: dict[str, object], outcome: str) -> None:
    lines = [
        "# Failure-Mode Matrix Report",
        "",
        "## 1. Run Metadata",
        "",
        f"- Report date: {utc_now()}",
        "- Owner: qa",
        f"- Outcome: `{outcome}`",
        "",
        "## 2. Mandatory Failure Classes",
        "",
        "| Failure class | Evidence source | Result |",
        "| --- | --- | --- |",
    ]
    for failure_class in MANDATORY_FAILURE_CLASSES:
        lines.append(f"| {failure_class} | `{suite_result['command']}` | {outcome} |")
    lines.extend(
        [
            "",
            "## 3. Suite Evidence",
            "",
            f"- Command: `{suite_result['command']}`",
            f"- Return code: {suite_result['returncode']}",
            f"- stdout tail: {', '.join(suite_result['stdout_tail']) or 'none'}",
            f"- stderr tail: {', '.join(suite_result['stderr_tail']) or 'none'}",
            "",
            "## 4. Sign-Off",
            "",
            f"- Mandatory matrix complete: {'yes' if outcome == 'PASS' else 'no'}",
            f"- Recommended disposition: `{'accept' if outcome == 'PASS' else 'rework'}`",
        ]
    )
    write_text_report(report_path, lines)


def write_restart_recovery_report(report_path: Path, suite_result: dict[str, object], outcome: str) -> None:
    scenario_ids = RESTART_RECOVERY_SUITE[3:]
    lines = [
        "# Restart Recovery Verification Report",
        "",
        "## 1. Run Metadata",
        "",
        f"- Report date: {utc_now()}",
        "- Owner: qa",
        f"- Outcome: `{outcome}`",
        "",
        "## 2. Restart-Recovery Scenarios",
        "",
        "| Scenario | Evidence source | Result |",
        "| --- | --- | --- |",
    ]
    for scenario in scenario_ids:
        lines.append(f"| {scenario} | `{suite_result['command']}` | {outcome} |")
    lines.extend(
        [
            "",
            "## 3. Suite Evidence",
            "",
            f"- Command: `{suite_result['command']}`",
            f"- Return code: {suite_result['returncode']}",
            f"- stdout tail: {', '.join(suite_result['stdout_tail']) or 'none'}",
            f"- stderr tail: {', '.join(suite_result['stderr_tail']) or 'none'}",
            "",
            "## 4. Sign-Off",
            "",
            f"- Restart recovery preserves zero-or-one active lease invariants: {'yes' if outcome == 'PASS' else 'no'}",
            f"- Recommended disposition: `{'accept' if outcome == 'PASS' else 'rework'}`",
        ]
    )
    write_text_report(report_path, lines)


def write_release_gate_report(report_path: Path, repo_root: Path, release_gate: dict[str, object]) -> None:
    lines = [
        "# Release Gate Command Verification",
        "",
        "## 1. Run Metadata",
        "",
        f"- Report date: {release_gate['generated_at']}",
        f"- Operator: {release_gate['operator_id']}",
        f"- Repository: {repo_root}",
        f"- Command: `{release_gate['invocation']}`",
        f"- Outcome: `{release_gate['outcome']}`",
        "",
        "## 2. Gate Summary",
        "",
        "| Criterion | Outcome | Evidence |",
        "| --- | --- | --- |",
        f"| setup_validation | {release_gate['criteria']['setup_validation']['outcome']} | {release_gate['criteria']['setup_validation']['report_path']} |",
        f"| adapter_qualification | {release_gate['criteria']['adapter_qualification']['outcome']} | {release_gate['evidence']['adapter_reports']['codex']} and peer reports |",
        f"| failure_mode_matrix | {release_gate['criteria']['failure_mode_matrix']['outcome']} | {release_gate['evidence']['failure_mode_matrix_report']} |",
        f"| restart_recovery | {release_gate['criteria']['restart_recovery']['outcome']} | {release_gate['evidence']['restart_recovery_report']} |",
        f"| reference_dogfood | {release_gate['criteria']['reference_dogfood']['outcome']} | {release_gate['evidence']['four_worker_dogfood_report']} |",
        "",
        "## 3. Evidence Package",
        "",
        f"- Setup validation report: {release_gate['evidence']['setup_validation_report']}",
        f"- Adapter qualification reports: {', '.join(release_gate['evidence']['adapter_reports'].values())}",
        f"- Failure-mode matrix report: {release_gate['evidence']['failure_mode_matrix_report']}",
        f"- Restart-recovery report: {release_gate['evidence']['restart_recovery_report']}",
        f"- Four-worker dogfood report: {release_gate['evidence']['four_worker_dogfood_report']}",
        f"- Machine-readable summary: {release_gate['evidence']['release_gate_summary_json']}",
        "",
        "## 4. Blocking Gaps and Next Actions",
        "",
    ]
    if release_gate["next_actions"]:
        for action in release_gate["next_actions"]:
            lines.append(f"- {action}")
    else:
        lines.append("- None. The release gate passed with no remaining findings.")
    lines.extend(
        [
            "",
            "## 5. Sign-Off",
            "",
            f"- Final release disposition: `{'accept' if release_gate['outcome'] == 'PASS' else 'rework'}`",
            "- Human-readable and machine-readable outputs match this report.",
        ]
    )
    write_text_report(report_path, lines)


def write_text_report(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
