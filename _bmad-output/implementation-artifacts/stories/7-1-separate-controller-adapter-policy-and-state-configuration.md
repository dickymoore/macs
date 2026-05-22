# Story 7.1: Separate controller, adapter, policy, and state configuration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want repo-local configuration domains for controller defaults, adapters, routing policy, governance, and state,
So that I can change orchestration behavior without editing code paths directly.

## Acceptance Criteria

1. MACS bootstraps and preserves separate repo-local configuration domains for controller defaults, adapter settings, routing policy, governance policy, and repo-local state layout. `macs setup init` creates or verifies dedicated files for each domain under the repo-local orchestration area, reports their path and status in human-readable and `--json` output, and does so without changing the existing top-level setup envelope or requiring code edits to tune workflow defaults or adapter availability.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-71-separate-controller-adapter-policy-and-state-configuration] [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption] [Source: _bmad-output/planning-artifacts/architecture.md#physical-architecture]
2. Operators can inspect the active configuration domains from the CLI without reverse-engineering the repo layout. A contract-shaped `macs setup check` reports the active controller defaults, adapter settings summary, routing policy, governance policy, and repo-local state paths plus workflow-class defaults in human-readable and `--json` output. The command stays read-only and keeps canonical nouns and compact output.  
   [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#primary-user-needs]
3. Controller and routing behavior consume the right configuration domain instead of hardcoded defaults. At minimum, controller-owned defaults such as the default workflow class for new tasks come from the controller config, routing still reads workflow-class policy from the routing policy file, governance remains separate, and state-path bootstrap comes from a dedicated state-layout domain while preserving current repo-local conventions by default.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-71-separate-controller-adapter-policy-and-state-configuration] [Source: _bmad-output/planning-artifacts/prd.md#functional-requirements] [Source: _bmad-output/project-context.md#critical-implementation-rules]
4. Runtime adapter settings are separately configurable and safely enforced. Repo-local adapter settings can enable or disable adapters and describe any adapter-local config reference without moving authority into adapter code. `macs adapter list`, `macs adapter inspect`, and adapter-backed worker registration or routing surfaces make disabled or configured adapters legible and fail closed when the repo-local adapter settings forbid new use.  
   [Source: _bmad-output/planning-artifacts/prd.md#installation-configuration-and-adoption] [Source: _bmad-output/planning-artifacts/prd.md#security--governance] [Source: _bmad-output/planning-artifacts/architecture.md#architectural-principles]
5. Repo-local state compatibility remains explicit. The new configuration domains preserve existing `.codex/orchestration/` defaults and keep compatibility with `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, and legacy fallback targeting behavior rather than scattering new hidden state or breaking current bridge usage.  
   [Source: _bmad-output/planning-artifacts/prd.md#compatibility--integration] [Source: _bmad-output/project-context.md#framework-specific-rules] [Source: tools/tmux_bridge/start_controller.sh] [Source: tools/tmux_bridge/start_worker.sh]
6. Regression coverage and docs prove the configuration split without regressing Story 6.4 governance defaults, Story 6.3 decision-rights enforcement, current setup bootstrap, or the frozen setup and adapter command envelopes.  
   [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md] [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]

## Tasks / Subtasks

- [x] Add one shared repo-local configuration-domain bootstrap and loader. (AC: 1, 3, 5)
  - [x] Add a narrow config-domain helper in `tools/orchestration/session.py` or a new adjacent `tools/orchestration/config.py` that bootstraps controller defaults, adapter settings, routing policy, governance policy, and state-layout files under the existing repo-local orchestration path.  
        [Source: tools/orchestration/session.py] [Source: tools/orchestration/policy.py] [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]
  - [x] Keep routing and governance policy files where current brownfield work expects them, and add the missing controller, adapter, and state-layout domains without renaming existing policy files out from under Story 6.4 behavior.  
        [Source: tools/orchestration/policy.py] [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]
  - [x] Preserve repo-local defaults under `.codex/orchestration/` while allowing the state-layout domain to declare the concrete file and directory paths MACS should use.  
        [Source: _bmad-output/planning-artifacts/prd.md#compatibility--integration] [Source: tools/orchestration/session.py]

- [x] Add read-only setup inspection for configuration domains. (AC: 1, 2, 5)
  - [x] Implement contract-listed `macs setup check` in `tools/orchestration/cli/main.py` so operators can inspect config domains, workflow defaults, adapter enablement, and state paths without touching raw files.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: tools/orchestration/cli/main.py]
  - [x] Extend `macs setup init` output to include the new config domains while preserving the existing envelope and startup-summary shape.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Keep `setup check` read-only and compact; setup validation or dry-run flows belong to Story 7.2, not this story.  
        [Source: _bmad-output/planning-artifacts/epics.md#story-72-deliver-mixed-runtime-setup-and-validation-flow]

- [x] Consume controller, adapter, and state config from the correct seams. (AC: 3, 4, 5)
  - [x] Move the default workflow class for `macs task create` into controller defaults rather than hardcoding it in CLI argument parsing alone.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/orchestration/tasks.py]
  - [x] Introduce repo-local adapter settings that at least support enabled or disabled status and a config reference or note per adapter, then surface and enforce that state through `adapter list`, `adapter inspect`, and new adapter usage paths such as registration.  
        [Source: tools/orchestration/adapters/registry.py] [Source: tools/orchestration/workers.py] [Source: tools/orchestration/cli/main.py]
  - [x] Make session bootstrap read the state-layout domain for authoritative repo-local state file paths while preserving legacy `.codex` targeting metadata outside the control-plane store.  
        [Source: tools/orchestration/session.py] [Source: tools/tmux_bridge/start_controller.sh] [Source: tools/tmux_bridge/common.sh]

- [x] Keep the story bounded to configuration separation, not full setup validation or migration docs. (AC: 2, 5)
  - [x] Do not implement full `setup validate`, `setup dry-run`, runtime installation walkthroughs, or release-evidence generation in this story.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#command-families] [Source: _bmad-output/planning-artifacts/epics.md#story-72-deliver-mixed-runtime-setup-and-validation-flow]
  - [x] Do not break or replace bridge-era files like `.codex/tmux-worker.env`, `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, or `tools/tmux_bridge/target_pane.txt`; Story 7.3 will own explicit migration and compatibility framing.  
        [Source: docs/customization.md] [Source: _bmad-output/planning-artifacts/epics.md#story-73-preserve-and-document-single-worker-compatibility-boundaries]
  - [x] Do not move routing or governance authority into adapter code or add remote or hosted config sources.  
        [Source: _bmad-output/planning-artifacts/architecture.md#architectural-principles] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

- [x] Add regression coverage and docs for the separated config domains. (AC: 6)
  - [x] Extend `tools/orchestration/tests/test_setup_init.py` with bootstrap and `setup check` coverage for the new config-domain files, controller defaults, and state-layout inspection.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
  - [x] Extend existing CLI contract tests where needed to prove disabled adapters fail closed and that task creation or assignment consumes the right config domain without breaking current envelopes.  
        [Source: tools/orchestration/tests/test_task_lifecycle_cli.py] [Source: tools/orchestration/tests/test_inspect_context_cli.py]
  - [x] Update operator docs so setup and customization guidance show the new repo-local config domains and their responsibilities.  
        [Source: README.md] [Source: docs/getting-started.md] [Source: docs/customization.md]

## Dev Notes

### Previous Story Intelligence

- Story 6.4 already established repo-local routing and governance policy files plus setup bootstrap reporting. Story 7.1 should keep those files stable and add the missing controller, adapter, and state-layout domains around them rather than replacing the policy seam.  
  [Source: _bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md]
- Story 6.3 hardened decision-rights behavior and setup or action envelopes. Keep setup-family and adapter-family top-level output shapes stable while adding configuration detail inside the current payloads.  
  [Source: _bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md]
- Epic 6 retrospective identified the main adoption risk entering Epic 7: repo-local behavior is spread across bootstrap files, policy files, tmux metadata files, and legacy targeting conventions, but MACS does not yet present them as one coherent configuration model.  
  [Source: _bmad-output/implementation-artifacts/epic-6-retro-2026-04-10.md]

### Brownfield Reuse Guidance

- `tools/orchestration/session.py` already owns repo-local path construction and bootstrap; extend that seam first for state-layout and setup config reporting.  
  [Source: tools/orchestration/session.py]
- `tools/orchestration/policy.py` already owns routing and governance policy defaults. Keep those files authoritative for policy and avoid burying them under a generic catch-all config blob.  
  [Source: tools/orchestration/policy.py]
- `tools/orchestration/cli/main.py` already renders `setup init`, adapter inspection, and task creation. The safest 7.1 path is to wire new config domains into those existing command families before inventing new ones.  
  [Source: tools/orchestration/cli/main.py]
- `tools/tmux_bridge/start_worker.sh` and `tools/tmux_bridge/start_controller.sh` already encode repo-local compatibility assumptions for worker env, tmux socket or session metadata, and target-pane state. Preserve those assumptions and document how the new control-plane config relates to them.  
  [Source: tools/tmux_bridge/start_worker.sh] [Source: tools/tmux_bridge/start_controller.sh]

### Technical Requirements

- Keep configuration repo-local and file-based under `.codex/orchestration/`; do not add a remote config fetch, hosted state service, or third-party dependency.
- Routing policy and governance policy remain separate configuration domains with their current semantics.
- Controller defaults must only contain controller-owned defaults, not policy or adapter authority.
- Adapter settings may describe enablement or runtime-specific config references, but adapters remain evidence providers rather than policy authorities.
- State-layout config must preserve the default `.codex/orchestration/` footprint and should only redirect paths within repo-local expectations.

### Architecture Compliance Notes

- Preserve the controller-authority boundary. Configuration may tune controller behavior, but it must not make adapters authoritative for ownership, routing, or recovery.
- Preserve the local-host-first and repo-local-state-first model from the architecture and PRD.
- Favor explicit, inspectable configuration files over hidden environment coupling or scattered new dotfiles.

### File Structure Requirements

- Prefer extending these files before introducing anything new:
  - `tools/orchestration/session.py`
  - `tools/orchestration/policy.py`
  - `tools/orchestration/cli/main.py`
  - `tools/orchestration/adapters/registry.py`
  - `tools/orchestration/workers.py`
  - `tools/orchestration/tests/test_setup_init.py`
  - `tools/orchestration/tests/test_task_lifecycle_cli.py`
  - `README.md`
  - `docs/getting-started.md`
  - `docs/customization.md`
- Add a small `tools/orchestration/config.py` helper only if the new controller, adapter, and state-layout domains would otherwise overload `session.py` or `policy.py`.

### Testing Requirements

- Run `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init` as the focused required validation surface.
- Run `python3 -m unittest discover -s tools/orchestration/tests` before marking the story done.
- Add regression cases for `setup check`, setup bootstrap of the new config files, controller-default workflow-class consumption, and disabled-adapter failure containment.
- Preserve current setup-init, governance-policy, and adapter-inspect regressions while expanding config visibility.

### Git Intelligence Summary

- `c3ccc6a` resolved recent review findings in controller-owned lifecycle and inspect seams.
- `51d2554` and `e474089` reinforced repo-local bootstrap and orchestration authority boundaries rather than introducing new subsystems.
- Recent changes continue to favor extending `policy.py`, `session.py`, `cli/main.py`, and existing test modules, which is the safest path for Story 7.1.

### Implementation Guardrails

- Do not implement full setup validation, migration evidence generation, or reference walkthroughs in this story.
- Do not rename or relocate current routing-policy or governance-policy files in a way that breaks Story 6.4.
- Do not introduce YAML, TOML, or third-party config libraries; stay stdlib-only and JSON-first unless an existing brownfield seam demands otherwise.
- Do not silently ignore disabled adapters; fail closed and make the reason visible.
- Do not scatter new hidden files outside existing repo-local conventions.

### Project Structure Notes

- This remains a brownfield, shell-first local orchestration controller.
- Story 7.1 should feel like a config-domain clarification and bootstrap hardening pass, not a rewrite of setup or runtime management.
- The best implementation path is to bootstrap the missing config files, surface them through `setup` and adapter commands, and thread a small number of real behaviors through those files so the separation is genuine.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/planning-artifacts/release-readiness-evidence-matrix.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/epic-6-retro-2026-04-10.md`
- `_bmad-output/implementation-artifacts/stories/6-4-govern-external-surfaces-privacy-sensitive-routing-and-audit-content.md`
- `_bmad-output/implementation-artifacts/stories/6-3-enforce-explicit-decision-rights-and-guarded-actions.md`
- `tools/orchestration/session.py`
- `tools/orchestration/policy.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/adapters/registry.py`
- `tools/orchestration/workers.py`
- `tools/tmux_bridge/start_worker.sh`
- `tools/tmux_bridge/start_controller.sh`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `tools/orchestration/tests/test_inspect_context_cli.py`
- `README.md`
- `docs/getting-started.md`
- `docs/customization.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Bootstrap the missing controller, adapter, and state-layout config domains first, while keeping routing and governance policy files stable.
- Add `setup check` and extend `setup init` in a narrow read-side slice before threading real behavior through controller defaults and adapter enablement.
- Finish with docs, required validation, and an explicit BMAD QA acceptance pass before marking the story done.

### Story Creation Notes

- Skill used: `bmad-create-story`
- Target story auto-discovered from `sprint-status.yaml` after Epic 6 was completed and its optional retrospective was recorded.
- Inputs reviewed for this story: Epic 7 story definition, PRD installation and compatibility requirements, architecture repo-local storage and authority rules, operator CLI contract, release-readiness setup evidence expectations, Epic 6 retrospective findings, current git history, live policy and bootstrap seams, bridge-era tmux metadata conventions, and the current setup, adapter, and task CLI tests.
- Validation pass applied against `.agents/skills/bmad-create-story/checklist.md`: the story now includes previous-epic learnings, the contract-listed `setup check` gap, exact brownfield reuse seams, anti-scope guardrails against bleeding into Stories 7.2 and 7.3, and regression expectations for disabled-adapter and state-path compatibility behavior.

### Debug Log References

- Story creation validation performed against `.agents/skills/bmad-create-story/checklist.md`
- `python3 -m unittest tools.orchestration.tests.test_task_lifecycle_cli tools.orchestration.tests.test_inspect_context_cli tools.orchestration.tests.test_setup_init`
- `python3 -m unittest discover -s tools/orchestration/tests`
- Explicit BMAD QA acceptance pass against Story 7.1 completed on 2026-04-10 after required validation; no remaining findings were identified.

### Completion Notes List

- Added repo-local `controller-defaults.json`, `adapter-settings.json`, and `state-layout.json` bootstrap alongside the existing routing and governance policy files under `.codex/orchestration/`.
- Implemented read-only `macs setup check` and expanded `macs setup init` output so operators can inspect config domains, workflow defaults, state paths, and compatibility paths without reading code.
- Moved `macs task create` default workflow-class selection into controller defaults and made session bootstrap consume repo-local state-layout path overrides.
- Added adapter-settings visibility and fail-closed enforcement for disabled adapters across `adapter inspect`, `adapter list`, worker registration, and routing rejection paths.
- Updated operator docs in `README.md`, `docs/getting-started.md`, and `docs/customization.md` to describe the separated config domains and their responsibilities.
- Required validations passed and the explicit BMAD QA acceptance pass found no remaining gaps. Full orchestration discovery finished green at 128 tests.

### File List

- `_bmad-output/implementation-artifacts/stories/7-1-separate-controller-adapter-policy-and-state-configuration.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tools/orchestration/config.py`
- `tools/orchestration/session.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/routing.py`
- `tools/orchestration/tasks.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/orchestration/tests/test_task_lifecycle_cli.py`
- `README.md`
- `docs/getting-started.md`
- `docs/customization.md`

### Change Log

- 2026-04-10: Created Story 7.1 with explicit config-domain bootstrap scope, `setup check` contract recovery, brownfield reuse guidance, compatibility guardrails, and regression targets.
- 2026-04-10: Implemented Story 7.1 config-domain bootstrap, setup inspection, controller-default workflow config, disabled-adapter enforcement, docs, validation, and explicit BMAD QA acceptance.
