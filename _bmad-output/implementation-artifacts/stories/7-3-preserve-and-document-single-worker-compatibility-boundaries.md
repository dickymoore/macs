# Story 7.3: Preserve and document single-worker compatibility boundaries

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an existing MACS user,
I want single-worker usage to remain supported with clear compatibility notes,
So that I can migrate incrementally instead of taking a hard workflow break.

## Acceptance Criteria

1. MACS surfaces explicit single-worker compatibility guidance on the controller-owned setup path. `macs setup check` and the conservative setup guidance surface document whether repo-local state migration is required, which legacy metadata files remain readable, and how one-worker mode fits the current control-plane model in both human-readable and `--json` output.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-73-preserve-and-document-single-worker-compatibility-boundaries] [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]
2. Compatibility notes clearly distinguish what remains supported unchanged versus what is superseded. The docs and setup surfaces state that existing tmux bridge metadata and direct helper scripts remain usable, while normal orchestration, assignment, inspection, intervention, and recovery are now expected to happen through controller-owned `macs` commands.  
   [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#contract-decisions] [Source: _bmad-output/project-context.md#critical-implementation-rules]
3. Single-worker mode remains a supported specialization of the same control-plane model. The compatibility guidance and regression coverage prove that a one-worker repo-local session can still use the same bootstrap, discovery, registration, and task lifecycle model without separate architecture or bespoke migration code.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-73-preserve-and-document-single-worker-compatibility-boundaries] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan] [Source: _bmad-output/planning-artifacts/architecture.md#runtime-topology]
4. Legacy metadata boundaries stay explicit and auditable. The implementation preserves readability of the existing repo-local metadata conventions already used by MACS, including `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, and the legacy `tools/tmux_bridge/target_pane.txt` fallback, without inventing a destructive migration step.  
   [Source: _bmad-output/planning-artifacts/architecture.md#runtime-topology] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan] [Source: _bmad-output/project-context.md#critical-implementation-rules]
5. Docs and migration examples align with live behavior. `README.md` and `docs/getting-started.md` explain the single-worker migration path, no-migration-required boundary, supported unchanged helpers, and the command mapping from older manual supervision habits to the controller-owned orchestration surface.  
   [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#adopter-setup-and-onboarding] [Source: _bmad-output/project-context.md#code-quality--style-rules]
6. Regression coverage proves the compatibility boundary without regressing Story 7.1 config separation, Story 7.2 setup validation, or existing tmux targeting and discovery behavior.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-architecture] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md]

## Tasks / Subtasks

- [x] Add a shared migration and compatibility summary for setup surfaces. (AC: 1, 2, 3, 4)
  - [x] Extend the existing setup helper seam so `setup check` and `setup dry-run` can emit explicit migration guidance, no-migration-required status, readable legacy metadata refs, unchanged helper paths, and superseded controller-owned command mappings without creating a separate migration subsystem.  
        [Source: tools/orchestration/setup.py] [Source: tools/orchestration/cli/main.py]
  - [x] Reuse the existing compatibility path resolution from Story 7.1 instead of hard-coding duplicate path logic in multiple CLI handlers.  
        [Source: tools/orchestration/config.py] [Source: tools/orchestration/session.py] [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]
  - [x] Keep the guidance explicit that single-worker mode is supported as a one-worker specialization of the control-plane model, not a second architecture track.  
        [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]

- [x] Surface compatibility guidance on the current controller-owned command path. (AC: 1, 2, 3)
  - [x] Extend `macs setup check` human-readable and `--json` output with a stable compatibility or migration section that reports `state_migration_required`, readable legacy metadata, unchanged helper workflows, and superseded controller-owned command guidance.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-output]
  - [x] Extend `macs setup dry-run` so the conservative onboarding path includes a single-worker migration note and the exact command mapping for operators moving off ad hoc pane supervision.  
        [Source: tools/orchestration/setup.py] [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance]
  - [x] Keep the guidance read-only and documentary. Story 7.3 must not add a migration writer, state rewriter, or destructive compatibility command.  
        [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

- [x] Preserve legacy metadata readability and single-worker behavior without broadening scope. (AC: 3, 4, 6)
  - [x] Preserve current readability for `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, and `tools/tmux_bridge/target_pane.txt`; if code changes are required, keep them narrow and aligned with existing helper behavior.  
        [Source: tools/orchestration/workers.py] [Source: tools/tmux_bridge/common.sh] [Source: tools/tmux_bridge/set_target.sh]
  - [x] Do not broaden Story 7.3 into adapter contributor guidance, release evidence packaging, or a new command-alias expansion project unless the story requires a narrow compatibility guardrail.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-74-publish-contributor-facing-adapter-guidance] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md]

- [x] Document the migration boundary and command mapping. (AC: 2, 5)
  - [x] Update `README.md` and `docs/getting-started.md` with explicit guidance for current single-worker users: what still works unchanged, what is superseded by `macs` surfaces, and why no state migration is required.  
        [Source: README.md] [Source: docs/getting-started.md]
  - [x] Include an example single-worker path that uses the same bootstrap, discovery, registration, inspection, and lifecycle flow as multi-worker usage, while calling out unchanged direct bridge helpers where they still apply.  
        [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]
  - [x] Add a small dedicated migration note under `docs/` only if the compatibility story is materially clearer there than in the existing docs.  
        [Source: _bmad-output/project-context.md#code-quality--style-rules]

- [x] Add regression coverage for compatibility guidance and legacy metadata boundaries. (AC: 4, 6)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with compatibility and migration-guidance assertions for `setup check` and `setup dry-run`, including explicit `state_migration_required = false` style visibility.  
        [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Extend `tools/orchestration/tests/test_inspect_context_cli.py` or an adjacent high-signal test to lock in legacy target-pane readability or equivalent compatibility behavior already relied on by existing helper flows.  
        [Source: tools/orchestration/tests/test_inspect_context_cli.py] [Source: tools/tmux_bridge/common.sh]
  - [x] Run the existing Python validation surfaces and, if the compatibility seam touches tmux helper behavior directly, run the adjacent tmux bridge smoke test as an optional validation.  
        [Source: tools/tmux_bridge/tests/smoke.sh] [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Story 7.2 established the controller-owned setup helper in `tools/orchestration/setup.py` and already documents mixed-runtime onboarding. Story 7.3 should build on that same seam rather than inventing a second compatibility report path.  
  [Source: _bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md]
- Story 7.2 already exposed compatibility paths in `setup check`; Story 7.3 should turn those raw path refs into explicit migration guidance, not replace the existing setup-validation work.  
  [Source: _bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md]
- Story 7.1 separated repo-local config and state-path concerns cleanly. Story 7.3 should reuse the same `resolved_compatibility_paths(...)` data instead of re-deriving legacy metadata locations ad hoc.  
  [Source: _bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md]

### Brownfield Reuse Guidance

- `tools/orchestration/setup.py` is now the natural home for setup-family compatibility or migration summaries. Prefer adding a small guidance block there over inflating `cli/main.py` with more duplicated read logic.  
  [Source: tools/orchestration/setup.py]
- `tools/orchestration/workers.py` already reads `.codex/tmux-socket.txt` and `.codex/tmux-session.txt` during discovery context resolution. Preserve that behavior and document it explicitly instead of replacing it with a new migration mechanism.  
  [Source: tools/orchestration/workers.py]
- `tools/tmux_bridge/common.sh` already preserves legacy `tools/tmux_bridge/target_pane.txt` readability as a fallback behind repo-local `.codex/target-pane.txt`. Treat that as the compatibility contract to regression-lock rather than redesigning target-pane state.  
  [Source: tools/tmux_bridge/common.sh]
- Existing setup and inspect tests are already the highest-signal surfaces for compatibility verification. Prefer extending them instead of creating a parallel migration test harness.  
  [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]

### Technical Requirements

- Keep the migration guidance local-host-first and documentary. No hosted services, no state export/import step, and no destructive compatibility writer.
- Preserve the setup-family JSON envelope and canonical nouns. Any new migration or compatibility block should fit inside existing controller-owned setup outputs.
- Make the no-migration-required boundary explicit.
- Treat direct bridge helpers as still usable, but clearly superseded for normal orchestration work by `macs worker`, `macs task`, `macs lease`, `macs recovery`, and `macs overview`.
- Single-worker mode must continue to use the same control-plane entities and flows, not a separate code path with different semantics.

### Architecture Compliance Notes

- Existing single-controller/single-worker flows remain supported as a degenerate one-worker orchestration session. Preserve that model explicitly in docs and guidance.  
  [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]
- Legacy repo-local metadata remains readable during migration. Preserve readability before adding any new compatibility promise.  
  [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]
- New orchestration commands layer above existing helpers instead of replacing them immediately. Story 7.3 should clarify that boundary rather than forcing a clean break.  
  [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]

### File Structure Requirements

- Prefer extending these files before introducing new modules:
  - `tools/orchestration/setup.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/workers.py`
  - `tools/tmux_bridge/common.sh`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_inspect_context_cli.py`
  - `README.md`
  - `docs/getting-started.md`
- Add a small migration-focused doc under `docs/` only if the compatibility story becomes materially clearer there.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Add coverage for compatibility guidance visibility, no-migration-required reporting, unchanged legacy metadata readability, and explicit single-worker documentation surfaces.
- If helper-script compatibility behavior changes directly, run `bash tools/tmux_bridge/tests/smoke.sh` as an additional validation when feasible.

### Git Intelligence Summary

- `c3ccc6a` continued the BMAD track after review fixes and kept the recent work centered on controller-owned seams.
- `51d2554` and `e474089` remain the key signals that repo-local bootstrap and compatibility conventions should be extended, not replaced.
- The safest 7.3 path is to add migration guidance around the seams that already exist: setup-family summaries, worker discovery metadata, and target-pane fallback behavior.

### Implementation Guardrails

- Do not add a destructive migration command or state rewrite flow.
- Do not turn Story 7.3 into contributor adapter docs or release evidence packaging.
- Do not break the existing setup-family JSON shape to force a special migration mode.
- Do not promise compatibility beyond what the current code actually preserves and the tests can prove.
- Do not expand plural family aliases or other broad compatibility affordances unless a narrow, story-backed need emerges during implementation.

### Project Structure Notes

- This remains a brownfield orchestration controller that grew from single-worker supervision.
- Story 7.3 should tell current users how the old one-worker habits map to the new control-plane surface without pretending the old architecture still owns truth.
- The highest-value increment is explicit, auditable migration guidance plus regression-locked legacy metadata readability.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md`
- `tools/orchestration/setup.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/workers.py`
- `tools/tmux_bridge/common.sh`
- `tools/tmux_bridge/set_target.sh`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `README.md`
- `docs/getting-started.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Extend the setup helper first so compatibility guidance has one controller-owned source of truth.
- Prove the guidance in setup JSON and human-readable surfaces before widening into docs.
- Finish by regression-locking legacy metadata readability and running the required validation surfaces plus an explicit BMAD QA acceptance pass.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 7.2 was completed.
- Inputs reviewed for this story: Epic 7.3 story definition, PRD migration and compatibility guidance, architecture compatibility plan and runtime topology, project compatibility rules, operator contract decisions, Story 7.1 config-path work, Story 7.2 setup-helper work, live discovery and target-pane compatibility seams, current inspect/setup tests, and recent git history.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing migration-guidance seam, explicit no-migration-required output, live legacy metadata boundaries, brownfield reuse notes, and anti-scope guardrails against 7.4 and release packaging.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- Focused validation: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- Full regression validation: `python3 -m unittest discover -s tools/orchestration/tests`
- Optional compatibility validation: `bash tools/tmux_bridge/tests/smoke.sh`
- Explicit BMAD QA acceptance pass completed against Story 7.3 acceptance criteria, live setup output, legacy metadata boundaries, and doc alignment.

### Completion Notes List

- Extended `tools/orchestration/setup.py` so `setup check` and `setup dry-run` share one compatibility summary covering no-migration-required status, legacy metadata paths, unchanged helper workflows, and controller-owned command mappings.
- Updated `macs setup check` and `macs setup dry-run` human-readable and `--json` output to make single-worker migration boundaries explicit without adding a migration writer or state rewrite flow.
- Updated `README.md` and `docs/getting-started.md` with a clear single-worker migration boundary, unchanged helper list, superseded controller-owned command mapping, and example one-worker control-plane flow.
- Added regressions in `test_setup_init.py` for compatibility guidance and in `test_inspect_context_cli.py` for legacy `target_pane.txt` fallback readability.
- The explicit BMAD QA acceptance pass found one final gap: `setup dry-run` human-readable output did not list the legacy metadata paths. That gap was fixed and regression-covered before the story was marked done.

### File List

- `_bmad-output/implementation-artifacts/stories/7-3-preserve-and-document-single-worker-compatibility-boundaries.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/setup.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `tools/orchestration/tests/test_setup_init.py`

### Change Log

- 2026-04-10: Created Story 7.3 with single-worker compatibility, migration-guidance, legacy metadata, documentation, and regression scope under Epic 7.
- 2026-04-10: Implemented Story 7.3, passed required validation, ran the optional tmux bridge smoke test, completed an explicit BMAD QA acceptance pass, and fixed the final dry-run legacy-metadata visibility gap before marking done.
