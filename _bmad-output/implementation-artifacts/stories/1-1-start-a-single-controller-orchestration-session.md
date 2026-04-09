# Story 1.1: Start a single-controller orchestration session

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want to launch a repo-local orchestration session with an exclusive controller lock,
so that only one authoritative controller can govern local worker state at a time.

## Acceptance Criteria

1. Given a repository with MACS installed, when I start an orchestration session, then MACS creates or verifies the repo-local `.codex/orchestration/` layout and acquires a single-controller lock.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-11-start-a-single-controller-orchestration-session]
2. Given an active controller session already owns the repo-local lock, when a second controller start attempt occurs, then MACS exits safely with an operator-visible message that identifies the active session and confirms controller state did not change.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-11-start-a-single-controller-orchestration-session] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]
3. The bootstrap preserves current brownfield behavior: root launchers stay thin, `tools/tmux_bridge/` remains the low-level transport layer, and existing `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, `.codex/target-pane.txt`, and legacy `tools/tmux_bridge/target_pane.txt` conventions remain readable.  
   [Source: _bmad-output/planning-artifacts/architecture.md#implementation-architecture] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan] [Source: _bmad-output/project-context.md#critical-implementation-rules]
4. The session bootstrap is structured so later Epic 1 stories can layer persistence and restart recovery on top of it without relocating the new control-plane entrypoints.  
   [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-1-control-plane-bootstrap-and-authority-foundation] [Source: _bmad-output/planning-artifacts/architecture.md#boot-sequence]

## Tasks / Subtasks

- [ ] Add the Phase 1 orchestration bootstrap module under `tools/orchestration/` instead of expanding `tools/tmux_bridge/` with controller-authority logic. (AC: 1, 3, 4)
  - [ ] Create the initial module shape needed for session bootstrap, with a reusable entrypoint that can be called from the existing shell launcher flow. Recommended brownfield fit: `tools/orchestration/controller.py` plus any minimal helper module required for session paths/lock metadata.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]
  - [ ] Ensure the bootstrap creates or verifies `.codex/orchestration/` and any subdirectories needed immediately by Phase 1 without pre-creating later-story artifacts unnecessarily. For Story 1.1 the required artifact is `controller.lock`; `state.db` and `events.ndjson` belong to Story 1.2.  
        [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]
  - [ ] Keep root launchers `start-controller` and `start-controller.sh` thin wrappers. If integration changes are needed, make them in `tools/tmux_bridge/start_controller.sh` and delegate authority bootstrap into `tools/orchestration/`.  
        [Source: start-controller] [Source: start-controller.sh] [Source: _bmad-output/project-context.md#language-specific-rules]

- [ ] Implement exclusive controller-lock acquisition and conflict reporting. (AC: 1, 2)
  - [ ] Acquire a repo-local lock at `.codex/orchestration/controller.lock` before any controller-authoritative work proceeds.  
        [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/planning-artifacts/architecture.md#boot-sequence]
  - [ ] Persist enough lock metadata for an operator-visible conflict message to point to the active session, at minimum covering repo path, PID, session identifier or tmux session, and acquisition timestamp. This is an implementation inference from the acceptance criteria plus the operator CLI requirement for clear action results.  
        [Inference from: _bmad-output/planning-artifacts/epics.md#story-11-start-a-single-controller-orchestration-session and _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output]
  - [ ] On conflict, fail closed: do not mutate controller-owned state, and print a human-readable message that tells the operator which session currently holds authority and what to inspect next.  
        [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#human-readable-status-conventions]

- [ ] Preserve current controller startup and tmux discovery behavior while inserting the new authority gate. (AC: 2, 3)
  - [ ] Keep support for `--repo`, `--tmux-session`, `--tmux-socket`, `--no-tmux-detect`, `--skip-skills`, and `--no-codex` intact.  
        [Source: tools/tmux_bridge/start_controller.sh]
  - [ ] Do not break repo-local writes to `.codex/macs-path.txt`, `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, and `.codex/tmux-bridge.sh`.  
        [Source: tools/tmux_bridge/start_controller.sh] [Source: README.md#quick-start]
  - [ ] Preserve current direct tmux helper usage and legacy target-pane fallback behavior; the new session lock must govern controller authority, not replace transport helpers.  
        [Source: tools/tmux_bridge/common.sh] [Source: docs/architecture.md#tmux-integration] [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]

- [ ] Add brownfield-safe regression coverage for bootstrap and lock contention. (AC: 1, 2, 3, 4)
  - [ ] Extend `tools/tmux_bridge/tests/smoke.sh` or add an adjacent shell integration test that verifies controller bootstrap creates `.codex/orchestration/controller.lock` in a temp repo and preserves existing `.codex/tmux-session.txt` / `.codex/tmux-socket.txt` behavior.  
        [Source: tools/tmux_bridge/tests/smoke.sh] [Source: _bmad-output/project-context.md#testing-rules]
  - [ ] Add a focused test for second-start rejection against the same repo-local orchestration directory. Keep tmux isolation and cleanup traps consistent with the existing smoke test style.  
        [Source: tools/tmux_bridge/tests/smoke.sh] [Source: _bmad-output/project-context.md#testing-rules]
  - [ ] If Python logic becomes non-trivial, prefer `python3 -m unittest` stdlib coverage over introducing third-party test dependencies.  
        [Inference from: _bmad-output/project-context.md#technology-stack--versions and _bmad-output/project-context.md#language-specific-rules]

- [ ] Update operator docs for the new bootstrap artifact and failure mode. (AC: 1, 2, 3)
  - [ ] Document that controller startup now establishes repo-local orchestration state under `.codex/orchestration/`.  
        [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]
  - [ ] Document the single-controller failure case and how the operator can identify the active session without resorting to manual guesswork.  
        [Source: _bmad-output/planning-artifacts/prd.md#user-success] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#experience-principles]

## Dev Notes

### Story Intent

Story 1.1 is the authority bootstrap for the entire Phase 1 control plane. It should not attempt to deliver persistence, leases, routing, or recovery semantics yet. Its job is to establish one repo-local controller authority boundary and a stable bootstrap seam for Stories 1.2 through 1.4.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-1-control-plane-bootstrap-and-authority-foundation]

### Brownfield Baseline

- Current controller entrypoints are the repo-root wrappers `start-controller` and `start-controller.sh`, both of which exec `tools/tmux_bridge/start_controller.sh`.
- Current tmux bridge state already writes under `.codex/` and reads legacy target-pane state during migration.
- The repo does not yet contain a `tools/orchestration/` module tree, so Story 1.1 should introduce it with the smallest viable bootstrap surface.

[Source: start-controller]  
[Source: start-controller.sh]  
[Source: tools/tmux_bridge/start_controller.sh]  
[Source: tools/tmux_bridge/common.sh]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Technical Requirements

- Keep the implementation local-host-first and repo-local. Do not introduce network services, hosted state, or non-local authority assumptions.  
  [Source: _bmad-output/planning-artifacts/prd.md#mvp---minimum-viable-product]
- Python 3.8+ stdlib is the preferred controller-core stack; do not add third-party Python dependencies for session bootstrap or file locking.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]
- Shell remains the primary operator surface. The controller bootstrap should be callable from the existing shell startup path rather than replacing it with a new top-level workflow.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/project-context.md#development-workflow-rules]
- Controller authority must remain separate from worker/runtime behavior. The lock governs controller authority only.  
  [Source: _bmad-output/project-context.md#framework-specific-rules] [Source: _bmad-output/planning-artifacts/architecture.md#architectural-principles]

### Architecture Compliance

- Acquire the single-controller session lock first in the boot sequence.  
  [Source: _bmad-output/planning-artifacts/architecture.md#boot-sequence]
- Reuse `tools/tmux_bridge/` only for low-level pane operations; keep new orchestration state logic outside that directory.  
  [Source: _bmad-output/planning-artifacts/architecture.md#implementation-architecture]
- Preserve compatibility with existing single-controller/single-worker usage as the degenerate one-worker case.  
  [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]
- Preserve existing repo-local metadata and legacy target-pane readability during migration.  
  [Source: _bmad-output/planning-artifacts/architecture.md#compatibility-plan]

### File Structure Requirements

- Root wrappers to preserve: `start-controller`, `start-controller.sh`
- Existing brownfield transport layer to preserve: `tools/tmux_bridge/`
- New Story 1.1 authority code should start under: `tools/orchestration/`
- New repo-local control-plane state root: `.codex/orchestration/`
- Required new bootstrap artifact for this story: `.codex/orchestration/controller.lock`
- Explicitly avoid scattering orchestration authority files elsewhere under hidden directories.

[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]  
[Source: _bmad-output/project-context.md#critical-dont-miss-rules]

### Testing Requirements

- Follow the current tmux smoke-test pattern: dedicated temporary sockets, temporary sessions, and cleanup traps so the user’s live tmux environment is untouched.  
  [Source: tools/tmux_bridge/tests/smoke.sh] [Source: _bmad-output/project-context.md#testing-rules]
- Cover both happy-path bootstrap and second-controller rejection.
- Treat state transitions explicitly in tests: directory created, lock acquired, second start blocked, existing `.codex/tmux-*` files preserved or still written correctly.
- Keep testing close to current tooling unless the new Python module genuinely needs unit-level isolation.

### Git Intelligence Summary

Recent commits focused on tmux targeting reliability and controller polling behavior:

- `19acf1e` Fix gitignore for local generated files
- `996c9f1` Fix tmux target pane reliability
- `98912ea` / `82d2c3a` ShellCheck sourcing fixes
- `e5bc885` Clarify controller polling behavior

Implication for Story 1.1: preserve auto-targeting, repo-local state files, and shell quality conventions instead of rewriting the controller startup path wholesale.

### Previous Story Intelligence

No prior story files exist yet in `_bmad-output/implementation-artifacts/stories/`. Story 1.1 sets the baseline patterns the rest of Epic 1 will inherit.

### Implementation Guardrails

- Do not create `state.db` or `events.ndjson` as the primary deliverable here unless a harmless empty-file bootstrap is unavoidable for wiring; authoritative persistence belongs to Story 1.2.  
  [Source: _bmad-output/planning-artifacts/epics.md#story-12-persist-authoritative-control-plane-entities]
- Do not embed routing, worker registration, or lease logic into session bootstrap.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]
- Do not move or duplicate low-level tmux helper behavior into the new control-plane module.  
  [Source: _bmad-output/project-context.md#code-quality--style-rules]
- Do not rely on raw tmux state as the authority source; this story establishes the authority gate that later stories will build on.  
  [Source: _bmad-output/planning-artifacts/architecture.md#architectural-principles]

### Open Questions Saved During Analysis

- Should lock metadata be plain text, JSON, or SQLite-backed later migration scaffolding? The architecture does not freeze the on-disk lock-file format. Prefer a minimal, explicit format that is easy for operators to inspect and for later stories to extend.
- Should the bootstrap be exposed only through `start_controller.sh` in this story, or also via an early `macs setup init` shim? The frozen operator CLI contract includes `macs setup init`, but Sprint 1 language emphasizes preserving the existing start-controller flow first. Default to preserving `start_controller.sh` as the required entrypoint now and leave `macs setup init` as optional reuse if it does not expand scope.

### Project Structure Notes

- This is a brownfield repo with existing shell-first control flow and tmux bridge helpers.
- The architecture explicitly recommends a split between new orchestration modules in `tools/orchestration/` and unchanged transport helpers in `tools/tmux_bridge/`.
- There are currently no implementation-artifact story files, so this story should establish the pattern of placing dedicated stories under `_bmad-output/implementation-artifacts/stories/`.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `README.md`
- `docs/architecture.md`
- `docs/getting-started.md`
- `tools/tmux_bridge/start_controller.sh`
- `tools/tmux_bridge/common.sh`
- `tools/tmux_bridge/tests/smoke.sh`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Skill used: `bmad-create-story`
- Story source set loaded from requested planning artifacts plus current brownfield repo files

### Completion Notes List

- Implemented repo-local orchestration bootstrap under `tools/orchestration/` with a direct `macs setup init` entrypoint and a reusable controller-lock bootstrap path for `start_controller.sh`.
- Preserved the existing tmux bridge compatibility shell while inserting controller authority gating before Codex launch.
- Added focused orchestration tests for direct CLI bootstrap, `--json` contract usage, lock contention, and the real `start_controller.sh` launcher path with a fake `codex` binary.
- Extended the tmux smoke test to cover repo-wrapper fallback when the saved tmux socket file is stale but `TMUX_SOCKET` is valid.
- Verified the implementation with `python3 -m unittest discover -s tools/orchestration/tests` and `./tools/tmux_bridge/tests/smoke.sh`.

### File List

- `_bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md`
- `README.md`
- `macs`
- `tools/orchestration/__init__.py`
- `tools/orchestration/cli/__init__.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/session.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/tmux_bridge/start_controller.sh`
- `tools/tmux_bridge/tests/smoke.sh`
