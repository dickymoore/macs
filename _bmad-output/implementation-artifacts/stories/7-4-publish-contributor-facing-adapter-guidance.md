# Story 7.4: Publish contributor-facing adapter guidance

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a contributor,
I want clear docs for adapter extension, declared capabilities, and validation expectations,
So that I can add or update runtime support without tribal knowledge.

## Acceptance Criteria

1. Contributors can find the minimum adapter contract in one authoritative place. MACS publishes a contributor-facing guide that explains the required facts, required operations, optional enrichments, bounded-evidence model, and first-class qualification expectations using the same canonical nouns already used on the controller surface.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-74-publish-contributor-facing-adapter-guidance] [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#contributor-adapter-flow-specification]
2. Declared capability modeling is explicit and aligned with current controller behavior. The contributor guidance and live adapter inspect surface explain how adapters expose worker capabilities, how those capabilities map to workflow-class-aware routing defaults, and which reference capability labels are currently used by Phase 1 policy and tests.  
   [Source: _bmad-output/planning-artifacts/prd.md#because-this-is-a-developer-tool-contributor-extensibility-is-part-of-the-product-not-just-an-implementation-detail] [Source: _bmad-output/planning-artifacts/architecture.md#routing-and-policy-engine] [Source: tools/orchestration/policy.py]
3. Degraded-mode expectations stay explicit instead of hidden in code. Contributors can see how missing optional runtime signals must be declared, how unsupported features differ from broken contract support, and how degraded behavior preserves controller authority semantics.  
   [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/architecture.md#first-class-adapter-qualification] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr19]
4. Qualification and validation expectations align with the shared contract suite and release-gate criteria already planned for Epic 8. The contributor guide and current `macs adapter inspect|validate` output point to the shared contract checks, focused regression commands, and the release-gate criteria that must be satisfied before runtime support can be treated as first-class.  
   [Source: _bmad-output/planning-artifacts/architecture.md#contract-tests] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg1] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#rg8]
5. The contributor guidance ships with documentation and regression coverage in the same increment. `README.md` and the contributor guide link to the live adapter commands and extension flow, and regression tests lock the contract fields and human-readable contributor-facing output so the surface cannot drift silently.  
   [Source: _bmad-output/planning-artifacts/prd.md#examples-and-migration-guidance] [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md#nfr21] [Source: _bmad-output/project-context.md#testing-rules]

## Tasks / Subtasks

- [x] Create one authoritative contributor-facing adapter guide. (AC: 1, 2, 3, 4, 5)
  - [x] Add a dedicated guide under `docs/` that explains the minimum adapter contract, capability declaration model, degraded-mode expectations, qualification steps, and current validation commands in one place instead of scattering contributor guidance across setup and operator docs.  
        [Source: docs/] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#contributor-adapter-flow-specification]
  - [x] Ground the guide in current code seams, including `BaseTmuxAdapter`, registry descriptors, repo-local routing defaults, and existing `macs adapter` verbs.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/adapters/registry.py] [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/policy.py]
  - [x] Keep the guide explicit that adapters remain bounded evidence providers and must not mutate controller authority semantics.  
        [Source: _bmad-output/project-context.md#framework-specific-rules] [Source: _bmad-output/planning-artifacts/architecture.md#runtime-adapter-architecture]

- [x] Expose the contributor contract on the existing adapter CLI seam. (AC: 1, 2, 3, 4)
  - [x] Extend adapter descriptors or validation payloads so `macs adapter inspect --json` and `macs adapter validate --json` expose required facts, required operations, capability-model references, degraded-mode expectations, unsupported features, and qualification expectations without forcing contributors to read controller internals.  
        [Source: tools/orchestration/adapters/base.py] [Source: tools/orchestration/cli/main.py]
  - [x] Extend the human-readable adapter inspect or validate output so contributors can see the same contract and qualification summary in plain text from the terminal.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#adapter-inspect] [Source: tools/orchestration/cli/main.py]
  - [x] Reuse existing shared seams rather than inventing a separate contributor-only command family. Story 7.4 should strengthen `macs adapter` and docs, not create a parallel scaffolding subsystem.  
        [Source: _bmad-output/project-context.md#development-workflow-rules]

- [x] Make the capability model and degraded expectations concrete. (AC: 2, 3)
  - [x] Document and expose the Phase 1 reference workflow-class capability labels used by routing policy, including the current repo defaults for `documentation_context`, `planning_docs`, `solutioning`, `implementation`, `review`, and `privacy_sensitive_offline`.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#routing-and-policy-engine]
  - [x] Distinguish required contract support from optional enrichments and unsupported features in both docs and adapter inspect output.  
        [Source: _bmad-output/planning-artifacts/architecture.md#adapter-contract] [Source: tools/orchestration/adapters/base.py]
  - [x] Keep degraded-mode language aligned with the existing adapter descriptors and tests instead of inventing new health semantics in documentation only.  
        [Source: tools/orchestration/adapters/registry.py] [Source: tools/orchestration/tests/test_setup_init.py]

- [x] Align the published guidance with qualification and release evidence expectations. (AC: 4, 5)
  - [x] Tie the contributor guidance to the current shared validation surfaces: `macs adapter inspect`, `macs adapter validate`, focused unit tests, full regression suite, and the planned release evidence expectations for first-class qualification and contributor-guidance alignment.  
        [Source: _bmad-output/planning-artifacts/release-readiness-evidence-matrix.md] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Update `README.md` and any nearby contributor-facing doc entry point so adopters can find the new guide quickly from the existing operational documentation surface.  
        [Source: README.md] [Source: docs/customization.md]
  - [x] Do not broaden Story 7.4 into Epic 8 release automation, new scaffolding generators, or adapter runtime behavior beyond the narrow surfacing needed to make the contributor contract explicit.  
        [Source: _bmad-output/planning-artifacts/epics.md#epic-8-qualify-the-release-with-failure-drills-and-dogfooding]

- [x] Add regression coverage for the contributor contract surface. (AC: 4, 5)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with adapter inspect or validate assertions that lock the contributor-facing contract fields in `--json` output and human-readable output.  
        [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Add any narrow adjacent test needed to prove capability-model labels or degraded-mode guidance stay aligned with live adapter descriptors instead of drifting into documentation-only promises.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: tools/orchestration/adapters/base.py]
  - [x] Run the required Python validation surfaces before marking the story done, and use the explicit BMAD QA acceptance pass to compare docs, live CLI output, and the story contract before closing the story.  
        [Source: _bmad-output/project-context.md#testing-rules]

## Dev Notes

### Previous Story Intelligence

- Story 7.3 established the pattern of publishing migration and compatibility guidance on existing controller-owned seams first, then documenting it in `README.md` and `docs/`. Story 7.4 should do the same for contributor adapter guidance instead of creating a disconnected workflow.  
  [Source: _bmad-output/implementation-artifacts/stories/7-3-preserve-and-document-single-worker-compatibility-boundaries.md]
- Story 7.2 already made setup validation evidence-centric. Story 7.4 should reference those same validation surfaces where they matter for adapter qualification, not invent another readiness command.  
  [Source: _bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md]
- Epic 6 already made governance, decision rights, and bounded audit content explicit. Contributor guidance must preserve those controller and governance boundaries rather than implying adapters can bypass them.  
  [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]

### Brownfield Reuse Guidance

- `tools/orchestration/adapters/base.py` is the natural place to centralize shared contract metadata and validation expectations; avoid duplicating those lists across docs, CLI handlers, and tests.  
  [Source: tools/orchestration/adapters/base.py]
- `tools/orchestration/cli/main.py` already owns `macs adapter list|inspect|probe|validate`; extend those verbs rather than creating a new contributor command family.  
  [Source: tools/orchestration/cli/main.py]
- `tools/orchestration/policy.py` already encodes the canonical workflow-class defaults used for routing. Reuse those names as the reference capability model instead of creating a second vocabulary in docs.  
  [Source: tools/orchestration/policy.py]
- Existing adapter tests in `tools/orchestration/tests/test_setup_init.py` are the highest-signal place to lock the contributor contract, because they already cover `adapter list|inspect|validate` and live probe normalization.  
  [Source: tools/orchestration/tests/test_setup_init.py]

### Technical Requirements

- Keep adapter extension guidance local-host-first and Phase 1 scoped.
- Use the same canonical nouns across docs and CLI output: `worker`, `task`, `lease`, `lock`, `event`, and `adapter`.
- Make the capability model explicit without promising automatic scaffold generation or dynamic schema negotiation.
- Distinguish required contract support, optional enrichments, unsupported features, and degraded behavior clearly.
- Point qualification guidance at live validation commands and shared regression commands that contributors can run today.

### Architecture Compliance Notes

- Adapters remain bounded evidence providers; controller state stays authoritative for ownership, routing, recovery, and audit.  
  [Source: _bmad-output/planning-artifacts/architecture.md#runtime-adapter-architecture]
- First-class adapter status is evidence-based, not declarative. Story 7.4 should expose the criteria but must not mark provisional adapters as first-class by documentation alone.  
  [Source: _bmad-output/planning-artifacts/architecture.md#first-class-adapter-qualification]
- Contributor UX should explain mandatory surfaces, optional enrichments, degradation behavior, and validation readiness in one repeatable flow.  
  [Source: _bmad-output/planning-artifacts/ux-design-specification.md#contributor-adapter-flow-specification]

### File Structure Requirements

- Prefer extending these files before introducing new modules:
  - `tools/orchestration/adapters/base.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `README.md`
  - `docs/customization.md`
- Add a dedicated contributor guide under `docs/` if that is the clearest way to keep the extension workflow in one place.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Add regression coverage for contributor-facing adapter inspect or validate output, shared contract metadata, degraded-mode visibility, and qualification-command alignment.
- Run an explicit BMAD QA acceptance pass against the story file, docs, CLI output, and regression surfaces before closing the story.

### Git Intelligence Summary

- The recent Epic 7 work has kept setup, compatibility, and documentation changes anchored to existing controller seams instead of adding parallel workflows.
- The safest 7.4 path is to make the shared adapter contract explicit in one reusable code seam, then point docs and tests at that same seam.
- Epic 8 has not started yet, so Story 7.4 should publish guidance and contract visibility, not pre-implement the release gate.

### Implementation Guardrails

- Do not add a separate contributor scaffolding or code-generation subsystem.
- Do not broaden Story 7.4 into Epic 8 release automation or new qualification commands.
- Do not document capability names or validation expectations that the current code and tests cannot actually prove.
- Do not weaken the controller-authority or bounded-evidence model in the name of adapter flexibility.
- Do not bury the contributor workflow across multiple docs when one authoritative guide plus live CLI output can keep it explicit.

### Project Structure Notes

- This remains a brownfield control-plane repo where contributor extensibility is part of the product.
- Story 7.4 should turn the current adapter code and validation seams into something contributors can follow directly.
- The highest-value increment is one authoritative contributor guide backed by explicit CLI contract output and regression tests.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/stories/7-2-deliver-mixed-runtime-setup-and-validation-flow.md`
- `_bmad-output/implementation-artifacts/stories/7-3-preserve-and-document-single-worker-compatibility-boundaries.md`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/tests/test_setup_init.py`
- `README.md`
- `docs/customization.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Centralize the shared contributor-facing adapter contract metadata first so docs, CLI output, and tests reference the same source of truth.
- Extend `macs adapter inspect|validate` next, proving the live contract surface in small red-green slices before widening into docs.
- Finish with the contributor guide, doc entry-point updates, required validation, and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Story 7.3 was completed.
- Inputs reviewed for this story: Epic 7.4 story definition, PRD contributor-extensibility requirements, architecture adapter-contract and contract-test sections, UX contributor-flow requirements, release-readiness evidence matrix items NFR21/NFR22/RG1/RG8, Story 7.2 and 7.3 learnings, current adapter CLI seams, policy workflow defaults, current adapter tests, and recent repo docs.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes the missing live CLI seam, capability-model alignment, degraded-mode boundary, release-evidence alignment, brownfield reuse guidance, and anti-scope guardrails against accidental Epic 8 expansion.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- Focused validation: `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- Full regression validation: `python3 -m unittest discover -s tools/orchestration/tests`
- Optional validation: `bash tools/tmux_bridge/tests/smoke.sh`
- Explicit BMAD QA acceptance pass completed against Story 7.4 acceptance criteria, live `macs adapter inspect|validate` output, README and customization entry points, and `docs/adapter-contributor-guide.md`

### Completion Notes List

- Centralized shared contributor-facing adapter contract metadata in `BaseTmuxAdapter`, including required facts and operations, capability-model references, optional enrichments, degraded-mode expectations, qualification expectations, shared validation commands, and release-gate criteria.
- Extended `macs adapter inspect|validate` human-readable and `--json` output so contributors can see the same contract and qualification surface without reverse-engineering controller internals.
- Published a dedicated contributor guide in `docs/adapter-contributor-guide.md` and linked it from `README.md` and `docs/customization.md`.
- Added regression coverage in `test_setup_init.py` for contributor-facing contract fields and human-readable adapter guidance.
- The explicit BMAD QA acceptance pass found no remaining findings.

### File List

- `_bmad-output/implementation-artifacts/stories/7-4-publish-contributor-facing-adapter-guidance.md`
- `README.md`
- `docs/adapter-contributor-guide.md`
- `docs/customization.md`
- `tools/orchestration/adapters/base.py`
- `tools/orchestration/adapters/codex.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`

### Change Log

- 2026-04-10: Created Story 7.4 with contributor-guide, adapter-contract surfacing, capability-model alignment, validation, and regression scope under Epic 7.
- 2026-04-10: Implemented Story 7.4, passed required validation, ran the optional tmux bridge smoke test, completed an explicit BMAD QA acceptance pass, and closed the story with no remaining findings.
