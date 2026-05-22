# Setup Validation Report

## 1. Run Metadata

- Report date: 2026-04-14T09:49:48+00:00
- Operator: codexuser
- Repository: /home/codexuser/macs_dev
- Host OS: Linux
- Validation scope: claude, codex, gemini, local
- Outcome: `PARTIAL`

## 2. Goal

- Target repo outcome: prove repo-local setup is current enough to support the Phase 1 release gate
- Target runtimes in scope: claude, codex, gemini, local
- Whether this is fresh install, existing repo adoption, or migration: existing repo adoption

## 3. Preconditions

- Required local dependencies present: yes
- Repo-local state path: /home/codexuser/macs_dev/.codex/orchestration
- Known deviations from default setup: enabled adapter 'claude' runtime is not available on PATH; enabled adapter 'claude' has no registered workers; enabled adapter 'codex' has no registered workers; enabled adapter 'gemini' runtime is not available on PATH; enabled adapter 'gemini' has no registered workers; enabled adapter 'local' has no registered workers; no ready workers are currently registered

## 4. Setup Steps Executed

| Step | Command or action | Expected result | Actual result | Outcome |
| --- | --- | --- | --- | --- |
| Validate repo-local setup | `macs setup validate --json` | current readiness summary available | outcome `PARTIAL` | PARTIAL |

## 5. Ready-State Evidence

### Controller Facts

- State store initialized: yes
- Worker records present: no
- Routing defaults visible: yes
- Repo-local configuration domains visible: yes

### Adapter Signals

| Worker | Runtime | Readiness | Runtime binary | Ready workers | Interruptibility |
| --- | --- | --- | --- | --- | --- |
| claude | claude | not_ready | missing | 0 | controller_visible |
| codex | codex | not_ready | available | 0 | controller_visible |
| gemini | gemini | not_ready | missing | 0 | controller_visible |
| local | local | not_ready | not required | 0 | controller_visible |

## 6. Story and Requirement Check

| Story check | Evidence | Result |
| --- | --- | --- |
| Supported runtimes can be registered | enabled adapters: claude, codex, gemini, local | PASS |
| Worker readiness can be validated end to end | ready workers: 0 | PARTIAL |
| Routing defaults can be inspected without bespoke glue | workflow defaults: documentation_context, implementation, planning_docs, privacy_sensitive_offline, review, solutioning | PASS |

## 7. Artifacts

- Config files or examples referenced: /home/codexuser/macs_dev/.codex/orchestration/controller-defaults.json, /home/codexuser/macs_dev/.codex/orchestration/adapter-settings.json, /home/codexuser/macs_dev/.codex/orchestration/routing-policy.json, /home/codexuser/macs_dev/.codex/orchestration/governance-policy.json, /home/codexuser/macs_dev/.codex/orchestration/state-layout.json

## 8. Failures and Gaps

| Gap or failure | Severity | Blocking story/requirement | Next action | Owner |
| --- | --- | --- | --- | --- |
| enabled adapter 'claude' runtime is not available on PATH | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| enabled adapter 'claude' has no registered workers | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| enabled adapter 'codex' has no registered workers | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| enabled adapter 'gemini' runtime is not available on PATH | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| enabled adapter 'gemini' has no registered workers | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| enabled adapter 'local' has no registered workers | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |
| no ready workers are currently registered | medium | RG6 | resolve and rerun `macs setup validate --release-gate` | eng |

## 9. Sign-Off

- Safe-ready-state reached: no
- Remaining caveats: enabled adapter 'claude' runtime is not available on PATH; enabled adapter 'claude' has no registered workers; enabled adapter 'codex' has no registered workers; enabled adapter 'gemini' runtime is not available on PATH; enabled adapter 'gemini' has no registered workers; enabled adapter 'local' has no registered workers; no ready workers are currently registered
- Recommended disposition: `rework`
