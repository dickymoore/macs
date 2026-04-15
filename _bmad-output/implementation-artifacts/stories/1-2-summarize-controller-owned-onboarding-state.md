# Story 1.2: Summarize controller-owned onboarding state

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,  
I want the guide to summarize the repo's actual onboarding state,  
so that I can tell whether the repo is initialized, configured, partially ready, or safe-ready without inspecting raw state directly.

## Acceptance Criteria

1. Given a repo with any combination of bootstrap, configuration, runtime, and worker state, when I run `macs setup guide`, then the guide reports the current onboarding readiness outcome using controller-supported semantics derived from the existing setup checks and validation flow, and it never reports a readiness state higher than the underlying controller-owned facts support.  
   [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-12-summarize-controller-owned-onboarding-state] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#state-aware-guidance] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#reliability--safety]
2. Given an unbootstrapped repo, when I run `macs setup guide` or `macs setup guide --json`, then the guide surfaces a blocked/bootstrap-required onboarding summary derived from missing required setup paths, identifies the repo as not yet initialized or configured, and remains strictly read-only.  
   [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-classification-rules] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
3. Given a bootstrapped repo, when `build_setup_validation` yields `FAIL`, `PARTIAL`, or `PASS`, then the guide exposes the same readiness outcome and the minimum controller-owned state facts needed to explain it, including safe-ready-state, enabled adapters, registered worker count, ready worker count, and routing-default visibility.  
   [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-12-summarize-controller-owned-onboarding-state] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#setup-state-summary] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-view-model]
4. The human-readable guide renders the setup state summary as a first-class block before the next-action section, keeps the command-led briefing order intact, and stays ASCII-first and copy-paste durable without taking on later-story scope for grouped gap provenance, doc-reference mapping, or narrow-terminal polish.  
   [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#format-patterns] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#information-hierarchy] [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-21-explain-blocked-and-partial-gaps-with-provenance and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals]
5. The structured guide payload stays under the existing setup-family JSON envelope and extends the current `data.guide.current_state` summary in place instead of inventing a second onboarding contract.  
   [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-view-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required---json-output] [Source: tools/orchestration/cli/main.py]
6. Regression coverage lives in `tools/orchestration/tests/test_setup_init.py` and covers the unbootstrapped blocked summary plus validation-aligned partial and ready summaries in both JSON and human-readable forms, without creating an onboarding-only test harness.  
   [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#testing--validation-strategy] [Source: _bmad-output/project-context.md#testing-rules] [Source: docs/contributor-guide.md#contribution-workflow]

## Tasks / Subtasks

- [ ] Normalize the guide's setup-state summary in `tools/orchestration/setup.py` by reusing existing read-only builders instead of duplicating onboarding logic. (AC: 1, 2, 3, 5)
  - [ ] Add or refine an internal summary builder that derives the guide's current onboarding state from `build_setup_dry_run`, `build_setup_validation`, and existing required-path checks so one place owns the normalization logic.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#read-model-composition] [Source: tools/orchestration/setup.py]
  - [ ] Represent the pre-bootstrap guide state as blocked/bootstrap-required from missing required setup paths while keeping the command read-only and without pretending `setup validate` succeeded on an uninitialized repo.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#reliability--safety]
  - [ ] Reuse validation-backed fields for bootstrapped repos so `outcome`, `safe_ready_state`, `enabled_adapters`, `registered_workers`, `ready_workers`, and `routing_defaults_visible` remain controller-derived rather than onboarding-only inventions.  
        [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#state-aware-guidance] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#communication-patterns]

- [ ] Extend the existing `data.guide.current_state` payload with the minimum state facts operators and local automation need. (AC: 1, 3, 5)
  - [ ] Keep the current setup-family JSON envelope and `data.guide` nesting intact; evolve the nested state summary rather than adding a new top-level onboarding schema.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-envelope] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-view-model]
  - [ ] Separate controller facts from runtime hints in the summary fields and sourcing, so runtime binaries on `PATH` remain hints while controller state remains authoritative.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#user-mental-model] [Source: _bmad-output/project-context.md#framework-specific-rules]

- [ ] Render a compact setup-state summary block in `tools/orchestration/cli/main.py` before the next-action block. (AC: 2, 3, 4)
  - [ ] Show the minimum summary facts explicitly in human-readable output: outcome, current phase, bootstrap/config visibility, routing-default visibility, enabled adapters, and worker counts.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#setup-state-summary] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#feedback-patterns]
  - [ ] Keep formatting ASCII-first and copy-paste durable, and do not add grouped gap provenance, doc refs, or layout work that belongs to later guided-onboarding stories.  
        [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#implementation-guidelines] [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-21-explain-blocked-and-partial-gaps-with-provenance and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals]

- [ ] Extend the shared setup-family regression seam in `tools/orchestration/tests/test_setup_init.py`. (AC: 1, 2, 3, 4, 6)
  - [ ] Add an unbootstrapped guide test asserting the blocked/bootstrap-required summary, zeroed worker counts, and read-only behavior without creating `.codex/orchestration/`.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped]
  - [ ] Update or add partial and ready tests that compare guide summary fields against the controller-backed validation facts for the same repo state.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#maintainability--testability]
  - [ ] Add human-readable assertions for the new state-summary block instead of only checking next-action labels.  
        [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#testing--validation-strategy] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#information-hierarchy]

- [ ] Update operator-facing docs only if the visible setup-guide examples or behavior descriptions become inaccurate after the state-summary changes. (AC: 4)
  - [ ] Limit any required doc touches to the current onboarding surfaces (`README.md`, `docs/getting-started.md`, `docs/how-tos.md`, `docs/user-guide.md`) and defer canonical doc-reference mapping to Story 3.1.  
        [Source: docs/contributor-guide.md#when-to-touch-which-docs] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#documentation-integration]

## Dev Notes

### Story Intent

This story promotes the guide's onboarding-state summary from a minimal scaffold to a first-class, controller-owned briefing. It should answer "what state is this repo actually in?" using the existing setup read models, while staying out of later-story scope for deeper model explanation, grouped gap provenance, doc linking, and presentation hardening.

[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-12-summarize-controller-owned-onboarding-state]  
[Source: _bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md#the-solution]  
[Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#experience-mechanics]

### Epic Continuity

- Story 1.1 already created the `macs setup guide` command seam, read-only contract, and initial next-action scaffold.
- Story 1.3 later deepens the controller-model explanation and conservative step ladder; do not bloat Story 1.2 with additional theory beyond what the state summary needs.
- Story 2.1 later groups blocked and partial gaps by category and provenance; Story 1.2 should stop at the minimum facts needed to explain the current state.
- Story 2.2 later hardens the prioritized next-action rationale; keep current recommendation logic stable unless a summary-alignment issue forces a small correction.
- Story 3.1 later centralizes doc links, Story 3.2 later hardens narrow-terminal and `NO_COLOR` rendering, and Story 3.3 later freezes the stable JSON guidance contract.

Implementation consequence: extend the guide summary in place inside the existing setup seam, not by adding a second onboarding model.

[Source: _bmad-output/implementation-artifacts/stories/1-1-add-a-guided-onboarding-entry-point.md#epic-continuity]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-13-present-the-controller-model-and-conservative-order]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-21-explain-blocked-and-partial-gaps-with-provenance]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-22-recommend-the-next-safe-onboarding-action]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals]  
[Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-33-provide-stable-json-guidance-output]

### Previous Story Intelligence

- Story 1.1 already wired `guide` into the setup-family parser and dispatch flow and established `build_setup_guide(repo_root, paths)` as the reuse point for later guided-onboarding stories.
- The current `build_setup_guide` payload already exposes `bootstrap_detected`, `current_phase`, `outcome`, `safe_ready_state`, `enabled_adapters`, `registered_workers`, and `ready_workers` in `data.guide.current_state`, so Story 1.2 should refine and complete that summary rather than relocating it.
- `emit_setup_guide_human_readable` currently renders orientation, repo path, bootstrap detection, current phase, and outcome/ready-state before the next-command section, but it does not yet present the fuller setup-state summary the planning set calls for.
- `tools/orchestration/tests/test_setup_init.py` already covers the guide's pre-bootstrap read-only behavior and bootstrapped partial and ready JSON scenarios; reuse those fixtures and broaden the assertions instead of building a parallel harness.
- Story 1.1 intentionally deferred blocked/partial/pass hardening, canonical doc-link mapping, narrow-terminal polishing, and the final stable guide JSON contract.

[Source: _bmad-output/implementation-artifacts/stories/1-1-add-a-guided-onboarding-entry-point.md#completion-notes-list]  
[Source: _bmad-output/implementation-artifacts/stories/1-1-add-a-guided-onboarding-entry-point.md#implementation-guardrails]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/tests/test_setup_init.py]

### Brownfield Baseline

- `macs` remains the thin bash wrapper into `python3 -m tools.orchestration.cli.main --repo "$ROOT_DIR"`.
- `tools/orchestration/setup.py` already owns the setup read models for configuration snapshot, dry-run, validation, and the guide payload.
- `build_setup_validation` already computes the controller-backed facts Story 1.2 needs to reuse: readiness `outcome`, `safe_ready_state_reached`, adapter summary, worker summary, routing-default visibility, gaps, and next actions.
- `tools/orchestration/cli/main.py` already owns the guide's human-readable rendering order and the setup-family JSON envelope.
- Current user-facing docs already describe `setup guide` as a read-only onboarding summary, so only touch docs if the visible examples or claims become inaccurate.

[Source: macs]  
[Source: tools/orchestration/setup.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: README.md]  
[Source: docs/getting-started.md]  
[Source: docs/user-guide.md]  
[Source: docs/contributor-guide.md#repository-map]

### Technical Requirements

- Keep `macs setup guide` strictly read-only and repo-local; it must not create controller state, edit config, or auto-run follow-up onboarding commands.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#governance--safety-boundaries] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#safety--governance-boundaries]
- Reuse the existing setup-family read models and validation facts wherever possible; do not introduce a second readiness engine or onboarding-only source of truth.  
  [Source: _bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md#technical-approach] [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#maintainability--testability]
- Never report a readiness state higher than the underlying validation or controller-owned bootstrap facts support.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#reliability--safety]
- Keep the implementation in Python 3.8+ stdlib and current shell/Python seams; do not add third-party dependencies for this CLI slice.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]
- Preserve canonical MACS nouns, setup-family command grammar, and current readiness vocabulary; if the guide introduces a blocked pre-bootstrap classification, keep it clearly derived from bootstrap facts rather than renaming validation outcomes.  
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#contract-decisions] [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#format-patterns]
- Treat runtime binaries on `PATH` as hints and controller state as authority whenever guide summary fields pull in current setup facts.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#user-mental-model] [Source: _bmad-output/project-context.md#framework-specific-rules]

### Architecture Compliance

- `tools/orchestration/setup.py` should continue to own onboarding-state composition, phase derivation, and any new summary-normalization helper.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#architectural-boundaries]
- `tools/orchestration/cli/main.py` should continue to own parser wiring and human-readable rendering for the guide.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#architectural-boundaries]
- If a tiny rendering helper becomes useful, keep it adjacent to the current CLI rendering helpers; do not create a new onboarding package or shadow subsystem.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#structure-patterns]
- Keep the human-readable order aligned with the architecture and UX guidance: orientation first, then state summary, then next-step guidance.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#format-patterns] [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#information-hierarchy]
- Do not expand Story 1.2 into grouped gap provenance, doc-reference blocks, migration summaries, or final JSON-contract stabilization.  
  [Inference from: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-21-explain-blocked-and-partial-gaps-with-provenance and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-23-surface-migration-and-recovery-follow-ups and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples and _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-33-provide-stable-json-guidance-output]

### Suggested Implementation Shape

- Add or refine one internal helper in `tools/orchestration/setup.py` that normalizes the guide's current-state payload for both pre-bootstrap and validation-backed cases.
- For pre-bootstrap repos, derive the blocked/bootstrap-required summary from existing required-path checks and keep the summary explicit about bootstrap/config visibility being absent.
- For bootstrapped repos, populate the state summary from `build_setup_validation(repo_root, paths)["validation"]` and current phase helpers instead of re-deriving readiness facts manually.
- Keep `next_action` and `follow_up_commands` on the current guide seam unless a small alignment fix is required to make the new summary truthful.
- Make the CLI renderer show a compact Setup State Summary block before the command recommendations and keep the same information order in human-readable and JSON modes.

[Inference from: tools/orchestration/setup.py, tools/orchestration/cli/main.py, and _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#guidance-view-model]

### File Structure Requirements

- Primary implementation files for this story:
  - `tools/orchestration/setup.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_setup_init.py`
- Optional helper-only touch point if needed:
  - `tools/orchestration/cli/rendering.py`
- Docs to touch only if the visible guide examples become inaccurate:
  - `README.md`
  - `docs/getting-started.md`
  - `docs/how-tos.md`
  - `docs/user-guide.md`

[Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#requirements-to-structure-mapping]  
[Source: docs/contributor-guide.md#when-to-touch-which-docs]

### Testing Requirements

- Extend the existing setup-family regression seam in `tools/orchestration/tests/test_setup_init.py`; do not add an onboarding-only harness.  
  [Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#testing--validation-strategy]
- Add targeted coverage for the unbootstrapped blocked summary and keep asserting that `guide` remains read-only by leaving `.codex/orchestration/` absent.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#journey-1-fresh-repo-not-yet-bootstrapped]
- Keep bootstrapped partial and ready tests aligned with `build_setup_validation` facts so the guide summary cannot drift away from validation semantics.  
  [Source: _bmad-output/planning-artifacts/prd-macs-guided-onboarding.md#maintainability--testability]
- Add human-readable assertions for the state-summary block as well as JSON assertions for the nested summary fields.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md#testing-strategy]
- Prefer tmux-independent setup fixtures and seeded worker rows; this story is about summary truth, not live tmux discovery.  
  [Inference from: tools/orchestration/tests/test_setup_init.py and _bmad-output/project-context.md#testing-rules]

### Git Intelligence Summary

- Recent committed repo history is still dominated by the broad Phase 1 orchestration foundation (`b19e63d`) and the follow-on docs pass (`aa4f631`), so Story 1.2 should continue to extend the current brownfield seams instead of relocating setup logic.
- The current working tree already has uncommitted guided-onboarding changes in `tools/orchestration/cli/main.py`, `tools/orchestration/setup.py`, `tools/orchestration/tests/test_setup_init.py`, and the onboarding docs. Work with those edits rather than resetting or re-deriving them.

Implementation consequence: keep changes surgical inside the existing guide seam and preserve adjacent user edits.

### Implementation Guardrails

- Do not rework the guide into an interactive wizard, separate onboarding subsystem, or alternate readiness engine.  
  [Source: _bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md#what-makes-this-different]
- Do not solve Story 1.3's deeper controller-model explanation or conservative step ladder here.  
  [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-13-present-the-controller-model-and-conservative-order]
- Do not solve Story 2.1's grouped gap explanations and provenance labels here; keep Story 1.2 at the state-summary layer.  
  [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-21-explain-blocked-and-partial-gaps-with-provenance]
- Do not solve Story 3.1 doc-link mapping, Story 3.2 terminal-polish work, or Story 3.3 JSON-contract freeze here.  
  [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-31-link-guided-output-to-canonical-docs-and-examples] [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-32-render-guided-onboarding-for-narrow-and-no-color-terminals] [Source: _bmad-output/planning-artifacts/epics-macs-guided-onboarding.md#story-33-provide-stable-json-guidance-output]
- Do not revert or overwrite unrelated uncommitted onboarding edits already present in the working tree.  
  [Inference from current git status]

### Project Structure Notes

- This remains a brownfield repo with an already-shipping setup family and current guided-onboarding work in flight.
- The safest implementation path is to deepen the existing guide seam in `tools/orchestration/setup.py` and `tools/orchestration/cli/main.py`, then lock it down with `test_setup_init.py`.
- Story 1.2 should improve summary truth and operator comprehension without expanding the command surface or adding new repo-local artifacts.

[Source: _bmad-output/project-context.md#development-workflow-rules]  
[Source: docs/contributor-guide.md#before-you-change-anything]  
[Source: _bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md#selected-foundation-existing-macs-setup-surface]

### References

- `_bmad-output/planning-artifacts/product-brief-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/prd-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/architecture-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/ux-design-specification-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/epics-macs-guided-onboarding.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/1-1-add-a-guided-onboarding-entry-point.md`
- `README.md`
- `docs/contributor-guide.md`
- `docs/getting-started.md`
- `docs/how-tos.md`
- `docs/user-guide.md`
- `macs`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Normalize the guide's current-state summary in `tools/orchestration/setup.py` so both pre-bootstrap and validation-backed cases flow through one reusable path.
- Render the fuller setup-state summary in `tools/orchestration/cli/main.py` before the command recommendation block.
- Extend `tools/orchestration/tests/test_setup_init.py` for blocked, partial, and ready summary coverage in JSON and human-readable modes.
- Update onboarding docs only if the visible guide examples become inaccurate after the summary changes.

### Debug Log References

- Story authored with `bmad-create-story`.
- Used the initiative-specific tracker `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml` as the sprint source of truth for this slice.
- Loaded the guided-onboarding planning set (`product-brief`, `PRD`, `architecture`, `UX`, `epics`, `operator-cli-contract`, `project-context`) plus Story 1.1 and the current setup/guide code seam to avoid duplicating already-delivered entry-point work.

### Test Record

- Not run; story creation only.

### Completion Notes List

- Created the Story 1.2 implementation brief for the guided-onboarding initiative.
- Marked Story 1.2 as `ready-for-dev` in the initiative-specific sprint tracker.

### File List

- `_bmad-output/implementation-artifacts/stories/1-2-summarize-controller-owned-onboarding-state.md`
- `_bmad-output/implementation-artifacts/sprint-status-macs-guided-onboarding.yaml`

### Change Log

- 2026-04-14: Created Story 1.2 and moved the guided-onboarding tracker entry from `backlog` to `ready-for-dev`.
