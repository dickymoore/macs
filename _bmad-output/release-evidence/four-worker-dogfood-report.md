# Four-Worker Dogfood Report

## 1. Run Metadata

- Run ID: dogfood-release-gate-0a2ce83a
- Date: 2026-04-10T17:51:15+00:00
- Operator: codexuser
- Repository revision: c3ccc6a+dirty
- Scenario definition reference: tools.orchestration.dogfood:run_reference_dogfood
- Outcome: `PASS`

## 2. Worker Lineup

| Worker | Runtime | Adapter version | Initial readiness | Interruptibility | Notes |
| --- | --- | --- | --- | --- | --- |
| worker-codex-macs-dogfood-81d0d714-0 | codex | phase1-contract | ready | interruptible | controller and adapter evidence available |
| worker-claude-macs-dogfood-81d0d714-1 | claude | phase1-contract | ready | interruptible | controller and adapter evidence available |
| worker-gemini-macs-dogfood-81d0d714-2 | gemini | phase1-contract | ready | interruptible | controller and adapter evidence available |
| worker-local-macs-dogfood-81d0d714-3 | local | phase1-contract | ready | interruptible | controller and adapter evidence available |

## 3. Scenario Summary

- Workflow classes exercised: implementation, planning_docs, solutioning, privacy_sensitive_offline
- Tasks created: task-4c25fc18e3a9, task-09718e5e43d3, task-c51cb57daa85, task-8ffeb1367286
- Protected surfaces involved: src/reference/codex-implementation.txt, docs/reference/claude-planning.md, docs/reference/gemini-solutioning.md, ops/reference/local-private-checklist.md
- Planned intervention points: pause and resume task-c51cb57daa85
- Planned recovery or reroute points: none

## 4. Reference Timing Envelope

| Check | Target | Actual | Result |
| --- | --- | --- | --- |
| Worker discovery / inspection | <= 2s | 0.097s | PASS |
| Task assignment path | <= 5s | 0.157s | PASS |
| Degraded warning visibility | <= 10s | 0.074s | PASS |

## 5. Execution Record

| Step | Action | Expected result | Actual result | Outcome |
| --- | --- | --- | --- | --- |
| 1 | Start controller session | repo-local orchestration initialized | setup init passed | PASS |
| 2 | Confirm worker roster | four runtimes discovered | discovered 4 workers | PASS |
| 3 | Assign mixed-runtime tasks | four tasks routed across four runtimes | assigned 4 tasks | PASS |
| 4 | Inspect ownership and locks | task, lease, and lock visibility preserved | locks visible=4 | PASS |
| 5 | Review routing rationale | selected worker preserved in task inspection | task inspect routing decisions present | PASS |
| 6 | Exercise intervention | pause and resume succeeds with decision trail | pause event=evt-task-pause-3e2b811dedb6 | PASS |
| 7 | Exercise degraded warning visibility | controlled warning visible within envelope | warning after 0.074s | PASS |
| 8 | Close or archive tasks | all reference tasks closed cleanly | close commands completed | PASS |

## 6. Evidence Summary

### Controller Facts

- Ownership remained explicit: yes
- Lock state remained inspectable: yes
- Event history remained inspectable: yes
- No task showed more than one active lease: yes

### Adapter Signals

| Worker | Capability evidence | Freshness evidence | Health evidence | Budget/session evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| worker-codex-macs-dogfood-81d0d714-0 | capability_decl | 0s | ready | permission_surface | none |
| worker-claude-macs-dogfood-81d0d714-1 | capability_decl | 0s | ready | required_only | none |
| worker-gemini-macs-dogfood-81d0d714-2 | capability_decl | 0s | ready | required_only | none |
| worker-local-macs-dogfood-81d0d714-3 | capability_decl | 0s | ready | required_only | none |

### Untrusted Claims or Operator Notes

- Claims that required corroboration: adapter capture evidence was treated as supporting evidence only; controller state remained authoritative.
- Notes about runtime asymmetry or degraded telemetry: Warning timing was proven with controlled stale-evidence injection in repo-local state to keep Story 8.3 bounded and avoid reimplementing the Story 8.2 failure matrix. This report intentionally uses controlled stale-evidence injection for the NFR3 check.

## 7. Story Acceptance Check

| Epic 8.3 expectation | Evidence | Result |
| --- | --- | --- |
| Mixed-runtime orchestration flow completed | 4 tasks routed across codex, claude, gemini, and local workers | PASS |
| Ownership was visible during the run | task inspect controller_truth current_owner matched each assignment | PASS |
| Locks were visible during the run | lock list plus lock inspect showed active controller-managed locks | PASS |
| Routing rationale was visible during the run | task inspect preserved routing_decision selected worker data | PASS |
| Intervention support was usable | pause/resume succeeded with decision and task event trail | PASS |
| Artifacts are sufficient for repeatability and release review | report, summary JSON, pane captures, and command log were written | PASS |

## 8. Artifact Inventory

- Machine-readable outputs: /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-summary.json, /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-pane-captures.json, /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-artifacts/four-worker-dogfood-command-log.json
- Human-readable summaries: /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-report.md
- Event IDs or trace references: evt-startup-recovery-9a625f7ac2a1, evt-task-create-0aa494f8e161, evt-task-create-2d38b0149c11, evt-task-create-6abfae043a71, evt-worker-discover-cc62934b6b5a, evt-lease-activate-7a1161e7f504, evt-lease-activate-7f4fa75c40fd, evt-lease-activate-8d869d6502a8, evt-lease-activate-91086307e917, evt-lock-activate-8b3e06829ad9, evt-lock-activate-b17c50bcf011, evt-lock-activate-b552135a2bf5
- Screens, snapshots, or pane captures: codex:%0, claude:%1, gemini:%2, local:%3
- Related failure-drill reports: see `tools/orchestration/tests/test_failure_drills_cli.py` coverage from Story 8.2

## 9. Findings

| Finding | Severity | Affects Epic | Owner | Action |
| --- | --- | --- | --- | --- |
| None. The reference scenario passed with no remaining findings. | low | 8 | eng | Carry the committed artifact into Story 8.4 release-gate aggregation. |

## 10. Recommendation

- Dogfood run counts toward release gate: yes
- Caveats: Warning timing was proven with controlled stale-evidence injection in repo-local state to keep Story 8.3 bounded and avoid reimplementing the Story 8.2 failure matrix. The degraded-warning check used controlled stale-evidence injection to stay within story scope.
- Recommended next run or fix: wire this report and its summary JSON into the Story 8.4 release-gate command.
