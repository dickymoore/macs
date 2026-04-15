# Release Gate Command Verification

## 1. Run Metadata

- Report date: 2026-04-14T09:49:55+00:00
- Operator: codexuser
- Repository: /home/codexuser/macs_dev
- Command: `macs setup validate --release-gate`
- Outcome: `PARTIAL`

## 2. Gate Summary

| Criterion | Outcome | Evidence |
| --- | --- | --- |
| setup_validation | PARTIAL | /home/codexuser/macs_dev/_bmad-output/release-evidence/setup-validation-report.md |
| adapter_qualification | PASS | /home/codexuser/macs_dev/_bmad-output/release-evidence/adapter-qualification/codex-qualification-report.md and peer reports |
| failure_mode_matrix | PASS | /home/codexuser/macs_dev/_bmad-output/release-evidence/failure-mode-matrix-report.md |
| restart_recovery | PASS | /home/codexuser/macs_dev/_bmad-output/release-evidence/restart-recovery-verification-report.md |
| reference_dogfood | PASS | /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-report.md |

## 3. Evidence Package

- Setup validation report: /home/codexuser/macs_dev/_bmad-output/release-evidence/setup-validation-report.md
- Adapter qualification reports: /home/codexuser/macs_dev/_bmad-output/release-evidence/adapter-qualification/codex-qualification-report.md, /home/codexuser/macs_dev/_bmad-output/release-evidence/adapter-qualification/claude-qualification-report.md, /home/codexuser/macs_dev/_bmad-output/release-evidence/adapter-qualification/gemini-qualification-report.md, /home/codexuser/macs_dev/_bmad-output/release-evidence/adapter-qualification/local-qualification-report.md
- Failure-mode matrix report: /home/codexuser/macs_dev/_bmad-output/release-evidence/failure-mode-matrix-report.md
- Restart-recovery report: /home/codexuser/macs_dev/_bmad-output/release-evidence/restart-recovery-verification-report.md
- Four-worker dogfood report: /home/codexuser/macs_dev/_bmad-output/release-evidence/four-worker-dogfood-report.md
- Machine-readable summary: /home/codexuser/macs_dev/_bmad-output/release-evidence/release-gate-summary.json

## 4. Blocking Gaps and Next Actions

- enabled adapter 'claude' runtime is not available on PATH
- enabled adapter 'claude' has no registered workers
- enabled adapter 'codex' has no registered workers
- enabled adapter 'gemini' runtime is not available on PATH
- enabled adapter 'gemini' has no registered workers
- enabled adapter 'local' has no registered workers
- no ready workers are currently registered

## 5. Sign-Off

- Final release disposition: `rework`
- Human-readable and machine-readable outputs match this report.
