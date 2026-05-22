---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md
  - /home/codexuser/macs_dev/_bmad-output/project-context.md
  - /home/codexuser/macs_dev/README.md
  - /home/codexuser/macs_dev/docs/getting-started.md
  - /home/codexuser/macs_dev/docs/user-guide.md
  - /home/codexuser/macs_dev/docs/how-tos.md
  - /home/codexuser/macs_dev/docs/contributor-guide.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/operator-cli-contract.md
  - /home/codexuser/macs_dev/_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md
  - /home/codexuser/macs_dev/tools/orchestration/setup.py
  - /home/codexuser/macs_dev/tools/orchestration/cli/main.py
workflowType: 'architecture'
project_name: 'macs_dev'
user_name: 'Dicky'
date: '2026-04-14T11:24:00+01:00'
lastStep: 8
status: 'complete'
completedAt: '2026-04-14T11:24:00+01:00'
---

# Architecture Decision Document - MACS Guided Onboarding

## Executive Summary

MACS Guided Onboarding should be implemented as a thin, read-only guidance layer on top of the existing setup-family read model. The safest architecture is not a new onboarding subsystem. It is a composition of already-authoritative sources in `tools/orchestration/setup.py`, exposed through one new setup-family CLI verb and aligned docs.

The architectural goal is to help an operator answer five questions quickly:

- what MACS is governing
- what the repo state is right now
- why the current outcome is `BLOCKED`, `PARTIAL`, `FAIL`, or `PASS`
- what the next safe action is
- where the canonical deeper explanation lives

This design deliberately avoids:

- a second readiness engine
- a second state store
- hidden automation
- browser or full-screen TUI commitments
- broad CLI redesign outside onboarding

## Project Context Analysis

### Requirements Overview

The initiative has 30 functional requirements and 13 non-functional requirements. Architecturally they cluster into four areas:

- guided entry and orientation under the existing `macs setup` surface
- state-aware readiness interpretation using current controller-owned sources
- evidence-backed remediation plus documentation linkage
- accessibility, automation parity, and maintainability through current setup-family seams

The scale is medium. The work is narrow in product scope but sensitive in architectural constraints because the feature must stay aligned with already-implemented setup and validation behavior.

- Primary domain: brownfield CLI tooling
- Complexity level: medium
- Estimated architectural components: 5

### Technical Constraints & Dependencies

- The solution must remain local-host-first and repo-local.
- The current control-plane model and setup-state semantics remain authoritative.
- The new experience must live under the existing `macs setup` family.
- Human-readable output must stay usable in narrow terminals and `NO_COLOR` mode.
- Structured output must remain available where useful for automation or evidence capture.
- Brownfield compatibility notes around single-worker operation must remain accurate.

### Cross-Cutting Concerns Identified

- truth versus interpretation: the guide may summarize, but it may not redefine readiness
- read-only versus state-changing actions: every recommendation must preserve explicit operator control
- docs parity: the guide and canonical docs must describe the same onboarding order
- evidence provenance: runtime availability hints must remain distinguishable from controller facts
- supportability: maintainers should be able to use the same guide output to reproduce user issues

## Starter Template Evaluation

### Primary Technology Domain

Brownfield CLI tooling layered onto the existing MACS control plane.

### Starter Options Considered

No greenfield starter template is appropriate for this initiative. The work is explicitly an extension of the current repo and toolchain rather than a new application bootstrap.

### Selected Foundation: Existing MACS Setup Surface

The initiative should inherit the current implementation foundation:

- launcher: `./macs`
- CLI framework: `argparse` in `tools/orchestration/cli/main.py`
- setup read model: `tools/orchestration/setup.py`
- docs set: `README.md`, `docs/getting-started.md`, `docs/user-guide.md`, `docs/how-tos.md`, `docs/contributor-guide.md`
- regression seam: `tools/orchestration/tests/test_setup_init.py`

### Architectural Decisions Provided by Current Foundation

**Language & Runtime:** Python 3 invoked by a small bash wrapper.  
**CLI Surface:** top-level command families with setup-family subparsers already in place.  
**State Model:** repo-local control-plane config and state already exist under `.codex/orchestration/`.  
**Testing Model:** setup-family behavior already has a focused regression surface.  
**Documentation Model:** onboarding order is already described in docs and must stay canonical.

**Note:** Project initialization from a starter template is not applicable to this architecture because the initiative extends an existing codebase.

## Core Architectural Decisions

### Decision Summary

The onboarding feature will be delivered through one new read-only CLI verb:

```bash
macs setup guide
macs setup guide --json
```

The exact implementation principle is:

1. reuse setup snapshot, dry-run, and validation functions that already exist
2. derive a guidance view model from those results
3. render that view model in human-readable and JSON forms
4. keep all state-changing actions as referenced commands only

### CLI Command Surface

Add `guide` to the existing `setup` subparser family in `tools/orchestration/cli/main.py`.

Command behavior:

- human-readable by default
- `--json` for structured consumption
- read-only in all modes
- same repo targeting behavior as other setup commands

The guide is intentionally not an interactive wizard. The CLI should return one complete, state-aware onboarding briefing per invocation.

### Read Model Composition

`tools/orchestration/setup.py` remains the authority source for onboarding data. The new guide should compose, not replace, these existing capabilities:

- configuration snapshot from current setup check data
- conservative onboarding order from current dry-run data
- readiness outcome and gaps from current validation data
- compatibility and migration guidance already exposed by setup-family helpers

Recommended addition:

- `build_setup_guide(repo_root, paths) -> dict[str, object]`

This function should call and normalize existing read-only builders rather than duplicating their logic.

### Guidance View Model

The guide should return a stable view model with these sections:

```json
{
  "command": "macs setup guide",
  "read_only": true,
  "repo_root": "/path/to/repo",
  "orientation": {
    "summary": "Controller-owned setup guidance over current repo-local state.",
    "authority_note": "Runtime availability is a hint; controller facts determine readiness."
  },
  "current_state": {
    "bootstrap_detected": true,
    "outcome": "PARTIAL",
    "safe_ready_state": false,
    "current_phase": "register-workers",
    "enabled_adapters": ["claude", "codex", "gemini", "local"],
    "registered_workers": 0,
    "ready_workers": 0
  },
  "gaps": [
    {
      "category": "runtime_availability",
      "severity": "warning",
      "subject": "claude",
      "message": "enabled adapter runtime is not available on PATH",
      "provenance": "validation"
    }
  ],
  "next_actions": [
    {
      "priority": 1,
      "kind": "action",
      "command": "macs worker discover --json",
      "why": "No enabled adapters currently have registered workers"
    }
  ],
  "related_commands": [
    "macs setup dry-run --json",
    "macs setup validate --json"
  ],
  "doc_refs": [
    {
      "topic": "mixed-runtime onboarding",
      "path": "docs/getting-started.md"
    }
  ]
}
```

This is a presentation contract, not a second control-plane schema. It exists only to organize onboarding guidance cleanly.

### Guidance Classification Rules

The guide may classify the current phase for operator comprehension, but phase classification must be derived from existing controller facts and validation results.

Recommended derived phases:

- `bootstrap-required`
- `inspect-configuration`
- `register-workers`
- `validate-readiness`
- `ready`
- `recover-or-reconcile`

Derivation rules:

- missing required setup paths -> `bootstrap-required`
- bootstrap present but no actionable validation outcome yet -> `inspect-configuration`
- enabled adapters without registered workers -> `register-workers`
- registered workers but no ready-worker evidence -> `validate-readiness`
- safe-ready-state true -> `ready`
- intervention or recovery-related gaps referenced -> `recover-or-reconcile`

These labels are onboarding aids only and must never contradict the underlying validation outcome.

### Documentation Integration

The guide should include canonical documentation references instead of embedding long-form explanations. Keep a small, centralized doc-reference mapping in code close to the onboarding view model so that:

- gaps can point to the right docs section
- human-readable and JSON output share the same references
- docs drift is visible during implementation and tests

The guide should prefer repo-relative paths and stable anchors when available.

### Safety & Governance Boundaries

The guide must remain strictly read-only.

Forbidden behaviors:

- auto-installing runtimes
- auto-registering workers
- auto-editing adapter settings
- mutating controller state implicitly
- presenting readiness as higher than `setup validate` supports

Allowed behaviors:

- summarize setup facts
- interpret validation gaps
- recommend next commands
- link to docs
- point to intervention and recovery commands when relevant

### Testing & Validation Strategy

Use the current setup-family test seam rather than creating an isolated onboarding harness.

Primary regression scope:

- unbootstrapped repo -> blocked guidance
- configured but not ready repo -> partial guidance
- safe-ready repo -> pass guidance
- no-color and narrow rendering
- JSON shape stability
- doc-reference parity where concrete command examples are included

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 6 areas where future contributors could drift if not specified:

- command naming
- JSON field naming
- section ordering
- provenance labels
- doc reference formatting
- ownership of business logic versus rendering

### Naming Patterns

**CLI Naming Conventions**

- command verb: `guide`
- handler name: `handle_setup_guide`
- builder name: `build_setup_guide`
- output function name: `emit_setup_guide_result`

**JSON Naming Conventions**

- use `snake_case` field names
- preserve current setup-family names such as `safe_ready_state`
- use uppercase readiness outcomes only where current surfaces already do so

**Doc Reference Naming**

- use repo-relative file paths in output
- use topic labels that match doc headings or operator terminology

### Structure Patterns

**Project Organization**

- `tools/orchestration/setup.py` owns onboarding data composition
- `tools/orchestration/cli/main.py` owns parser registration and command dispatch
- rendering helpers may live in `tools/orchestration/cli/main.py` or a small helper module, but business rules stay in `setup.py`
- docs remain the canonical long-form explanation layer
- tests extend `tools/orchestration/tests/test_setup_init.py`

**File Structure Patterns**

- no new persistence files
- no new onboarding config files
- no new docs tree dedicated only to the guide
- no duplicate examples living outside the canonical docs set

### Format Patterns

**Human-Readable Output Order**

1. orientation
2. outcome and state summary
3. gaps or confirmations
4. primary next action
5. related commands
6. docs references

**Textual Markers**

- `[READ-ONLY]`
- `[ACTION]`
- `[DOC]`
- `[EVIDENCE]`
- `[MIGRATION]`

**Outcome Formatting**

- keep `BLOCKED`, `PARTIAL`, `FAIL`, and `PASS` exactly as current surfaces present them
- do not invent onboarding-only status vocabulary

### Communication Patterns

**Provenance Rules**

- controller facts: repo-local paths, routing defaults, registered workers, ready workers
- runtime hints: binary availability on `PATH`
- guide interpretation: derived next step and current phase
- docs: canonical deeper explanation

**Recommendation Rules**

- one primary next action first
- optional secondary actions after
- every mutating command labeled explicitly
- every recommendation includes a one-line why

### Process Patterns

**Drift Control**

- if guide copy and setup logic disagree, setup logic wins and guide copy must be corrected
- if docs and guide examples disagree, both must be updated in the same change set
- no copy-only onboarding changes without test and docs review

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
macs_dev/
├── macs
├── README.md
├── docs/
│   ├── contributor-guide.md
│   ├── getting-started.md
│   ├── how-tos.md
│   ├── index.md
│   └── user-guide.md
└── tools/
    └── orchestration/
        ├── cli/
        │   ├── main.py
        │   └── rendering.py
        ├── setup.py
        └── tests/
            └── test_setup_init.py
```

### Architectural Boundaries

**CLI Boundary**

- owns argument parsing and final rendering
- does not own readiness or guidance decision logic

**Setup Guidance Boundary**

- owns normalization of setup snapshot, dry-run, and validation data
- owns derived onboarding phase and next-action recommendations
- does not mutate controller state

**Documentation Boundary**

- owns long-form explanation and canonical examples
- is referenced by the guide rather than duplicated into it

**Regression Boundary**

- existing setup-family tests remain the primary contract surface
- doc updates must accompany command-surface changes

### Requirements to Structure Mapping

**Guided Entry & Orientation**

- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`

**State-Aware Guidance & Readiness Interpretation**

- `tools/orchestration/setup.py`
- `tools/orchestration/tests/test_setup_init.py`

**Docs & Learn-More Support**

- `README.md`
- `docs/getting-started.md`
- `docs/user-guide.md`
- `docs/how-tos.md`
- `docs/index.md`
- `docs/contributor-guide.md`

**Accessibility & Structured Output**

- `tools/orchestration/cli/main.py`
- `tools/orchestration/cli/rendering.py` if output helpers are extracted
- `tools/orchestration/tests/test_setup_init.py`

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** The architecture reuses the implemented setup-family model, so command shape, repo-local state, and brownfield constraints remain aligned.

**Pattern Consistency:** Business logic remains centralized in setup helpers while CLI code stays presentation-focused.

**Structure Alignment:** The affected files already own onboarding behavior, docs, and tests, so the slice can be implemented without creating shadow modules.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:** The design covers guided entry, readiness interpretation, remediation, documentation linkage, accessibility, automation parity, and maintainability.

**Non-Functional Requirements Coverage:** Performance, accessibility, truthfulness, and regression-test expectations all map directly to existing CLI and test seams.

### Implementation Readiness Validation ✅

**Decision Completeness:** The command surface, view model, boundaries, and file ownership are all specified.

**Structure Completeness:** The project structure identifies the exact code and docs surfaces to change.

**Pattern Completeness:** Naming, output ordering, provenance labels, and drift controls are defined clearly enough for consistent implementation.

### Gap Analysis Results

**Deferred by Design**

- persisted resume checkpoints for long onboarding sessions
- adaptive overview-console reuse beyond the CLI guide
- repo archetype profiles beyond the current MACS implementation

These are intentionally deferred because they would widen scope beyond the current implemented system.

### Validation Issues Addressed

- Rejected a browser or full-screen TUI direction because it would introduce a second surface without improving truth alignment.
- Rejected a greenfield starter-template mindset because the work must extend the current repo, not rebuild it.
- Chose `guide` as the CLI verb because it reads naturally under `macs setup` and matches the product goal without implying hidden automation.

### Architecture Completeness Checklist

**✅ Requirements Analysis**

- [x] Project context analyzed
- [x] Brownfield constraints identified
- [x] Documentation dependencies mapped
- [x] Cross-cutting concerns identified

**✅ Architectural Decisions**

- [x] CLI surface defined
- [x] read model composition defined
- [x] output contract defined
- [x] safety boundaries defined

**✅ Implementation Patterns**

- [x] naming rules defined
- [x] section ordering defined
- [x] provenance rules defined
- [x] drift-control rules defined

**✅ Project Structure**

- [x] affected files identified
- [x] boundaries established
- [x] requirements mapped to structure
- [x] test seam specified

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

This architecture is narrow enough to stay safe, specific enough to guide implementation, and grounded enough in the current MACS system to avoid reopening settled control-plane assumptions.
