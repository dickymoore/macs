# Setup Validation Template

Use this for Epic 7.2 setup, onboarding, migration, and safe-ready-state validation in a real repository.

## 1. Run Metadata

- Report date:
- Operator:
- Repository:
- Branch or revision:
- Host OS:
- tmux version:
- MACS revision:
- Validation scope:
- Outcome: `PASS | FAIL | PARTIAL | BLOCKED`

## 2. Goal

- Target repo outcome:
- Target runtimes in scope:
- Whether this is fresh install, existing repo adoption, or migration:

## 3. Preconditions

- Required local dependencies present:
- Required credentials or local runtime access present:
- Repo-local state path:
- Any known deviations from default setup:

## 4. Setup Steps Executed

| Step | Command or action | Expected result | Actual result | Outcome |
| --- | --- | --- | --- | --- |
| Install/configure MACS |  |  |  |  |
| Register Codex worker |  |  |  |  |
| Register Claude worker |  |  |  |  |
| Register Gemini worker |  |  |  |  |
| Register local worker |  |  |  |  |
| Inspect routing defaults |  |  |  |  |
| Validate worker readiness |  |  |  |  |
| Verify intervention path |  |  |  |  |
| Verify recovery example |  |  |  |  |

## 5. Ready-State Evidence

### Controller Facts

- Controller session lock acquired:
- State store initialized:
- Worker records present:
- Routing defaults visible:
- Repo-local configuration domains visible:

### Adapter Signals

| Worker | Runtime | Readiness | Freshness | Interruptibility | Budget/session signal | Notes |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

### Untrusted Claims or Manual Observations

- Pane-level observations:
- Manual notes that require corroboration:

## 6. Story and Requirement Check

| Story check | Evidence | Result |
| --- | --- | --- |
| Supported runtimes can be registered |  |  |
| Worker readiness can be validated end to end |  |  |
| Routing defaults can be inspected without bespoke glue |  |  |
| Reference examples exist for registration |  |  |
| Reference examples exist for intervention |  |  |
| Reference examples exist for recovery |  |  |

## 7. Artifacts

- Human-readable command transcript:
- Machine-readable output files:
- Event IDs:
- Snapshot paths:
- Config files or examples referenced:

## 8. Failures and Gaps

| Gap or failure | Severity | Blocking story/requirement | Next action | Owner |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 9. Sign-Off

- Safe-ready-state reached:
- Remaining caveats:
- Recommended disposition: `accept | rework | block`
