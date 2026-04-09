# Release Readiness Evidence Matrix

## Purpose

This matrix converts the remaining soft release expectations in the planning set into explicit verification targets. It focuses on the NFRs and release-gate expectations called out as still too interpretation-sensitive in the implementation readiness report, especially governance, adoption, compatibility, maintainability, documentation, and release evidence packaging.

Primary source basis:

- `prd.md` NFR7-NFR22 and MVP decision-rights model
- `architecture.md` sections on first-class adapter qualification, CLI/tmux operator surface, persistence and audit policy, compatibility plan, test architecture, and release-gated scenarios
- `ux-design-specification.md` sections on onboarding, contributor validation, machine-readable outputs, and follow-on artifacts
- `epics.md` Epic 7 and Epic 8 acceptance criteria
- `implementation-readiness-report-2026-04-09.md` readiness gaps and recommended next steps

## Owner Roles

- `ENG`: implementation owner for controller, adapters, CLI, and tests
- `QA`: verification owner for repeatable validation runs and evidence review
- `DOC`: documentation owner for operator, adopter, and contributor artifacts
- `UX`: operator-surface contract owner for terminology, output shape, and examples
- `REL`: release owner accountable for final gate review and sign-off

## Soft NFR Matrix

| ID | Expectation to Prove | Concrete Verification Method | Owner | Timing | Required Output Artifact |
| --- | --- | --- | --- | --- | --- |
| NFR7 | Adapter outputs remain bounded evidence, not authority | Run contract and integration tests that inject conflicting adapter claims and assert controller state, routing, and recovery decisions continue to rely on authoritative `worker/task/lease/lock/event` records; include one negative test per supported adapter | ENG | Adapter implementation complete; must pass before adapter can be marked release-candidate | `release-evidence/nfr7-bounded-evidence-report.md` |
| NFR8 | Defaults never trigger auto-push, autonomous remote work, or unapproved side effects | Review default config and command paths; run a policy regression suite proving high-consequence actions require operator confirmation and forbidden actions remain blocked under default policy | ENG | Before RC1 and on any policy-default change | `release-evidence/nfr8-default-safety-report.md` |
| NFR9 | Governed integrations support allowlisting or equivalent trust controls | Execute configuration and integration tests showing disabled-by-default governed surfaces, explicit allowlist configuration, and rejected enablement without trust controls | ENG | Before any governed integration is called production-oriented or first-class | `release-evidence/nfr9-governed-integration-report.md` |
| NFR10 | Runtime approval, sandbox, and permission controls are preserved and surfaced | For each supported runtime, run adapter qualification checks verifying MACS exposes runtime permission state in inspection output and never strips or bypasses approval boundaries during dispatch or intervention | ENG | Per adapter release gate | `release-evidence/runtime-permission-preservation-matrix.md` |
| NFR13a | Audit capture, retention, and redaction are bounded by documented local policy | Review audit schema and storage policy against implementation; run tests proving metadata is always retained, optional rich content obeys policy, and redacted output stays redacted in exports and snapshots | ENG | Before Epic 6 completion and again at final release gate | `release-evidence/audit-content-policy-verification.md` |
| NFR14 | Normal orchestration workflows do not require raw tmux as the primary path | Validate a canonical operator workflow set from CLI alone: inspect workers, assign work, inspect task/lease/lock state, pause, reroute, inspect recovery, and export events without relying on raw pane archaeology | QA | After Epic 4 completion; rerun at release candidate | `release-evidence/operator-surface-walkthrough-report.md` |
| NFR15 | A technically capable adopter can complete mixed-runtime local-host setup in a real repo without undocumented glue | Run a fresh-repo setup validation using only published docs and supported config; record steps, elapsed time, failures, and any undocumented intervention needed | QA | After Epic 7 setup flow lands; must pass before release decision | `release-evidence/setup-validation-report.md` |
| NFR16 | Terminology stays consistent across commands, inspectors, JSON output, and docs | Freeze the operator command contract, then run a terminology audit comparing CLI help, inspectors, JSON keys, docs, and screenshots/snapshots against canonical terms `worker/task/lease/lock/event` | UX | Before substantial Epic 4 polish and before docs freeze | `release-evidence/terminology-consistency-audit.md` |
| NFR17 | MVP remains local-host-first and does not require hosted backend infrastructure | Inspect install, runtime, and test flows for network or hosted-service dependencies; verify release path works on a single local host with repo-local state only | ENG | Before RC1 | `release-evidence/local-host-deployment-attestation.md` |
| NFR18 | Repo-local state and legacy targeting conventions remain compatible | Run migration and backward-compatibility checks against existing `.codex/target-pane.txt`, `tools/tmux_bridge/target_pane.txt`, and current repo-local state conventions; document readable legacy inputs and any required migration step | QA | After Epic 7 compatibility work; required before upgrade guidance is published | `release-evidence/compatibility-validation-report.md` |
| NFR19 | Missing optional runtime signals degrade safely without silent safety loss | Run per-adapter degraded-mode scenarios where optional telemetry is absent, stale, or partial; assert worker classification, routing eligibility, warnings, and intervention options remain explicit and safe | ENG | Per adapter qualification and again in failure-drill suite | `release-evidence/degraded-signal-behavior-report.md` |
| NFR20 | Control-plane logic stays testable through explicit entities and state transitions | Produce a test-to-domain trace showing unit and integration coverage for task, lease, lock, routing, intervention, and recovery state transitions, with no critical behavior reachable only through opaque side effects | ENG | Before Epic 8.1 closes | `release-evidence/control-plane-testability-trace.md` |
| NFR21 | Docs, examples, and regression coverage ship with behavior rather than later | Use a release checklist that blocks merge-to-release unless each user-facing feature has matching docs/examples and each new orchestration behavior has regression coverage linked from the release gate | REL | Continuous during Epic 7 and Epic 8; final check at release gate | `release-evidence/docs-and-regression-completeness-checklist.md` |
| NFR22 | Adapter extension points are explicit enough for contributors to extend safely | Conduct a contributor dry run using only published extension docs and shared contract tooling; require the contributor to declare capabilities, unsupported features, degraded behavior, and qualification results without reverse-engineering controller internals | DOC | After Epic 7.4 lands; required before claiming adapter extensibility is release-ready | `release-evidence/contributor-extension-dry-run-report.md` |

## Release-Gate Expectation Matrix

| ID | Release-Gate Expectation | Concrete Verification Method | Owner | Timing | Required Output Artifact |
| --- | --- | --- | --- | --- | --- |
| RG1 | First-class adapter qualification is evidence-based, not declarative | For each first-class adapter candidate, run shared contract tests, degraded-mode checks, intervention-path verification, routing-evidence verification, and supported-feature failure drills; require explicit unsupported-feature declarations | ENG | Per adapter candidate, before inclusion in release gate summary | `release-evidence/adapter-qualification/<adapter-name>-qualification-report.md` |
| RG2 | Mandatory failure-mode matrix is complete and repeatable | Execute the release-gated failure drills for worker disconnect, stale lease divergence, duplicate claim, split-brain ownership, lock collision, misleading health evidence, surfaced budget exhaustion, and interrupted recovery; capture authoritative state assertions and event traces for each class | QA | Before every release candidate and final release sign-off | `release-evidence/failure-mode-matrix-report.md` |
| RG3 | Restart recovery invariants are explicitly proven | Run restart scenarios with live leases, unreleased locks, degraded workers, and partial recovery; assert boot sequence freezes risky work, restores persisted state first, reconciles live evidence second, and records recovery outputs | QA | Included in RC validation and final gate | `release-evidence/restart-recovery-verification-report.md` |
| RG4 | Four-worker reference dogfood scenario proves mixed-runtime value under reference timing | Execute the defined four-worker flow in the MACS repo using the supported reference runtime mix; record timing, visible ownership, locks, routing rationale, intervention support, and repeatability notes | QA | Final pre-release validation after feature freeze | `release-evidence/four-worker-dogfood-report.md` |
| RG5 | One command produces both human-readable and machine-readable release status | Run the release-gate command and confirm it reports pass/fail for adapters, failure classes, restart recovery, and the dogfood scenario, with matching human output and `--json` output suitable for audit | ENG | After Epic 8.4 implementation; mandatory at release sign-off | `release-evidence/release-gate-command-verification.md` |
| RG6 | Setup validation evidence exists as part of the release package | Re-run the documented setup flow in a clean repository and archive the exact validation report referenced by the release gate so NFR15 is proven by current evidence, not prior ad hoc testing | QA | At RC1 and refresh if setup docs change materially | `release-evidence/setup-validation-report.md` |
| RG7 | Compatibility and migration claims are backed by current evidence | Re-run the single-worker migration and repo-local compatibility checks and attach the resulting report to the release package; release cannot rely on narrative compatibility claims alone | QA | Before final release note and migration guide publication | `release-evidence/compatibility-validation-report.md` |
| RG8 | Contributor-facing adapter guidance aligns with qualification reality | Compare contributor docs and templates against the actual qualification workflow, then run one dry-run adapter update or scaffold exercise to confirm the published guidance matches the contract and gate criteria | DOC | Before adapter extensibility is called release-ready | `release-evidence/contributor-guidance-alignment-report.md` |

## Minimum Evidence Package for Phase 1 Release Review

The release package should not be considered complete until it contains, at minimum:

1. One current adapter qualification report per first-class adapter candidate.
2. One current failure-mode matrix report covering all mandatory failure classes.
3. One restart recovery verification report.
4. One four-worker dogfood report from the reference repository.
5. One setup validation report from a clean-repo run.
6. One compatibility validation report covering single-worker migration and repo-local state conventions.
7. One release-gate command verification report showing both human-readable and `--json` outputs.
8. One current audit-content policy verification report.
9. One current terminology consistency audit.
10. One contributor extension dry-run or guidance-alignment report.

## Notes

- This matrix intentionally treats evidence artifacts as required release inputs, not optional supporting documents.
- If a planned artifact is replaced by a differently named deliverable, the replacement should preserve the same proof obligation and traceability.
- The matrix assumes the separate operator CLI contract artifact will freeze final command names, canonical nouns, and required `--json` surfaces before Epic 4 and Epic 7 implementation hardens.
