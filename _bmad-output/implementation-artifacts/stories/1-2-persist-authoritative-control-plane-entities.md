# Story 1.2: Persist authoritative control-plane entities

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want durable storage for `worker`, `task`, `lease`, `lock`, and `event` records,
so that controller truth survives process restarts and normal orchestration activity.

## Acceptance Criteria

1. Given an active orchestration session, when the controller creates or mutates control-plane entities, then the canonical entity state is committed transactionally in `state.db`.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-12-persist-authoritative-control-plane-entities]
2. Given an active orchestration session, when a material control-plane transition occurs, then MACS also appends an audit record to `events.ndjson` for operator inspection and replay-friendly export.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-12-persist-authoritative-control-plane-entities] [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
3. The persistence layer preserves controller authority boundaries introduced in Story 1.1: authoritative state lives under `.codex/orchestration/`, hangs off the `tools/orchestration/` seam, and does not make tmux observations or adapter output the source of truth.  
   [Source: _bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md#dev-notes] [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#framework-specific-rules]
4. The new persistence foundation is restart-safe for later Epic 1 stories: the schema, write path, and event model are structured so Story 1.3 can enforce invariants against authoritative records and Story 1.4 can load persisted state during boot without relocating core modules.  
   [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-1-control-plane-bootstrap-and-authority-foundation] [Source: _bmad-output/planning-artifacts/architecture.md#boot-sequence]

## Tasks / Subtasks

- [x] Add the control-plane persistence module under `tools/orchestration/` and keep it separate from `tools/tmux_bridge/`. (AC: 1, 3, 4)
  - [x] Introduce a brownfield-fit persistence package, for example `tools/orchestration/store.py` and `tools/orchestration/schema.py`, or an equivalent minimal split that keeps schema/bootstrap concerns separate from session-lock code.  
        [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout] [Source: _bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md#tasks--subtasks]
  - [x] Extend the existing session bootstrap in `tools/orchestration/session.py` so Story 1.2 creates or verifies `state.db` and `events.ndjson` under `.codex/orchestration/` without relocating the Story 1.1 entrypoints.  
        [Source: tools/orchestration/session.py] [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]
  - [x] Keep root launchers and `macs setup init` thin; persistence wiring should remain reusable from the current bootstrap seam rather than introducing a second authority path.  
        [Source: tools/orchestration/cli/main.py] [Source: tools/tmux_bridge/start_controller.sh]

- [x] Define the MVP authoritative schema for controller-owned entities and supporting audit tables in SQLite. (AC: 1, 3, 4)
  - [x] Create tables for `workers`, `tasks`, `leases`, `locks`, and `events`, plus the architecture-recommended supporting tables needed to avoid later migration churn: `routing_decisions`, `evidence_records`, `recovery_runs`, and `policy_snapshots`.  
        [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
  - [x] Model the required fields the architecture calls out for each entity, even if some fields are initially nullable until later stories populate them. This includes `current_worker_id` and `current_lease_id` on `tasks`, replacement linkage on `leases`, and aggregate or actor metadata on `events`.  
        [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model]
  - [x] Choose deterministic primary-key and timestamp storage conventions that are easy to inspect from both Python and shell-based operator workflows. This is an implementation inference from the repo’s shell-first operating model and the need for replayable audit records.  
        [Inference from: _bmad-output/project-context.md#technology-stack--versions and _bmad-output/planning-artifacts/architecture.md#persistence-strategy]

- [x] Implement transactional write helpers that treat SQLite as canonical state and NDJSON as audit export. (AC: 1, 2, 3)
  - [x] Provide a single write path that mutates authoritative rows and inserts the corresponding `events` row inside one SQLite transaction before appending the matching record to `events.ndjson`.  
        [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
  - [x] Fail closed if the SQLite transaction cannot commit; do not emit NDJSON records for transitions that never became authoritative.  
        [Inference from: _bmad-output/planning-artifacts/architecture.md#write-model]
  - [x] Treat `events.ndjson` as an export mirror of authoritative events, not a second source of truth. The SQLite `events` table remains authoritative for later inspect and recovery commands.  
        [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-json-payload-patterns]
  - [x] Ensure event payloads retain the minimum metadata later CLI and recovery stories will need: `event_id`, `event_type`, aggregate refs, actor identity, timestamp, correlation fields, and payload or redaction metadata.  
        [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-object-state-fields-in-json]

- [x] Expose a narrow bootstrap or diagnostic surface that proves persistence is live without over-scoping Story 1.2 into full task lifecycle commands. (AC: 1, 2, 4)
  - [x] Extend `macs setup init` output to confirm whether `state.db` and `events.ndjson` were created or verified, keeping output compact and compatible with the frozen CLI envelope.  
        [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#required-human-readable-output] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#json-envelope]
  - [x] If a dedicated internal seed or probe helper is needed for tests, keep it under `tools/orchestration/` and avoid exposing premature public verbs like `macs task create` before Story 4.2.  
        [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]

- [x] Add regression coverage for schema bootstrap, transactional writes, and audit mirroring. (AC: 1, 2, 3, 4)
  - [x] Extend `tools/orchestration/tests/` with stdlib `unittest` coverage that verifies `setup init` now materializes `state.db` and `events.ndjson` in the repo-local orchestration directory.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Add focused Python tests for at least one successful entity mutation that commits SQLite rows and appends exactly one NDJSON event, plus one failure-path test that proves NDJSON is not appended when the transaction fails.  
        [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
  - [x] Keep tmux-dependent coverage limited to bootstrap wiring; entity persistence tests should run without needing a live tmux server.  
        [Inference from: tools/orchestration/tests/test_setup_init.py and _bmad-output/project-context.md#testing-rules]
  - [x] Preserve existing Story 1.1 lock-contention coverage while updating its expectations from “files absent” to “files bootstrapped” where appropriate.  
        [Source: _bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md#completion-notes-list]

- [x] Update operator-facing documentation for the new authoritative artifacts and audit behavior. (AC: 2, 3)
  - [x] Update `README.md` and any directly affected getting-started text so `.codex/orchestration/state.db` and `.codex/orchestration/events.ndjson` are documented as repo-local control-plane artifacts.  
        [Source: README.md] [Source: docs/getting-started.md]
  - [x] Document the authority split clearly: SQLite is canonical state, NDJSON is append-friendly audit export, and tmux/runtime signals remain evidence rather than direct state mutation.  
        [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules] [Source: _bmad-output/project-context.md#critical-dont-miss-rules]

## Dev Notes

### Story Intent

Story 1.2 is the persistence foundation for the Phase 1 control plane. It should make controller-owned state durable and auditable, but it should not yet implement lease invariants, restart reconciliation, worker registration, or full task lifecycle commands. Its output is a trustworthy storage layer that later stories can enforce and recover from.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]

### Previous Story Intelligence

- Story 1.1 already established the new authority seam in `tools/orchestration/`, with `tools/orchestration/session.py` handling repo-local bootstrap and `macs setup init` / `tools/tmux_bridge/start_controller.sh` reusing that seam.
- Story 1.1 intentionally deferred `state.db` and `events.ndjson`; its tests currently assert those files do not exist after bootstrap, so Story 1.2 must update those expectations deliberately rather than accidentally breaking them.
- Story 1.1 preserved compatibility files such as `.codex/tmux-session.txt`, `.codex/tmux-socket.txt`, and `.codex/macs-path.txt`; Story 1.2 must continue to treat those as transport metadata, not authoritative control-plane records.

[Source: _bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md#implementation-guardrails]  
[Source: tools/orchestration/session.py]  
[Source: tools/orchestration/tests/test_setup_init.py]  
[Source: tools/tmux_bridge/start_controller.sh]

### Brownfield Baseline

- The repo is shell-first, but the new controller seam is Python stdlib code under `tools/orchestration/`.
- `macs setup init` already exists and is the narrowest current public entrypoint for orchestration bootstrap.
- `tools/tmux_bridge/` remains the transport layer and should not absorb control-plane persistence responsibilities.
- There is not yet any controller-owned entity store or schema module in `tools/orchestration/`.

[Source: _bmad-output/project-context.md#technology-stack--versions]  
[Source: tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#implementation-architecture]

### Technical Requirements

- Use SQLite in `state.db` for durable indexed authoritative state and invariant enforcement; do not replace it with JSON files, YAML, or a hosted database.  
  [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]
- Use append-friendly NDJSON in `events.ndjson` for audit export, debugging, and future replay tooling.  
  [Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]
- Keep the implementation local-host-first and repo-local under `.codex/orchestration/`.  
  [Source: _bmad-output/planning-artifacts/prd.md#mvp---minimum-viable-product]
- Stay within Python 3.8+ stdlib unless an explicit blocker is discovered; `sqlite3`, `json`, `pathlib`, and `contextlib` should be sufficient here.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]
- Treat writes as part of the orchestration contract: deterministic filenames, UTF-8 text for NDJSON, and explicit transaction boundaries for SQLite.  
  [Source: _bmad-output/project-context.md#language-specific-rules]

### Architecture Compliance

- Authoritative records live in SQLite with transactional writes; audit events are stored both in SQLite and in append-only NDJSON export.  
  [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
- Each controller action must read authoritative state, validate invariants or policy, write entity mutations plus events in one transaction, then record side-effect results explicitly rather than pretending side effects are reversible.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Worker runtime state, adapter outputs, and tmux observations remain evidence only. Only the controller mutates authoritative task, lease, lock, and routing state.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- This story should lay the groundwork for boot-sequence recovery by ensuring persisted state can be loaded before new assignments in Story 1.4.  
  [Source: _bmad-output/planning-artifacts/architecture.md#boot-sequence]

### Suggested Implementation Shape

- Extend `tools/orchestration/session.py` only for path/bootstrap duties such as ensuring `state.db` and `events.ndjson` exist.
- Introduce a dedicated persistence module under `tools/orchestration/` for schema creation, connection management, and transactional write helpers.
- Keep CLI wiring minimal in `tools/orchestration/cli/main.py`; do not let the CLI own storage semantics directly.
- If test helpers are needed, keep them in `tools/orchestration/tests/` or as internal Python helpers, not shell-only fixtures.

[Inference from: tools/orchestration/session.py, tools/orchestration/cli/main.py, and _bmad-output/planning-artifacts/architecture.md#persistence-strategy]

### File Structure Requirements

- Existing authority seam to extend: `tools/orchestration/session.py`
- Current CLI entrypoint to preserve: `tools/orchestration/cli/main.py`
- Preferred location for new persistence code: `tools/orchestration/`
- Repo-local authoritative artifacts to create in this story:
  - `.codex/orchestration/state.db`
  - `.codex/orchestration/events.ndjson`
- Existing transport layer to leave as transport-only: `tools/tmux_bridge/`

[Source: tools/orchestration/session.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#suggested-storage-layout]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface for persistence work.  
  [Source: README.md#testing]
- Test state transitions explicitly: schema bootstrapped, tables created, canonical row committed, event mirrored, and failure path leaves audit export unchanged.  
  [Source: _bmad-output/project-context.md#testing-rules]
- Keep tmux-isolated shell coverage for launcher integration only; persistence semantics should be testable without a live worker pane.  
  [Inference from: tools/orchestration/tests/test_setup_init.py]
- Maintain brownfield safety by preserving Story 1.1’s single-controller lock tests while extending bootstrap assertions to include persistence artifacts.  
  [Source: _bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md#completion-notes-list]

### Git Intelligence Summary

Recent commits remain centered on tmux stability and shell hygiene:

- `19acf1e` Fix gitignore for local generated files
- `996c9f1` Merge pull request #10 from dickymoore/fix/tmux-target-pane-reliability
- `98912ea` Fix shellcheck source path
- `82d2c3a` Fix shellcheck sourcing hints
- `e5bc885` Clarify controller polling behavior

Implication for Story 1.2: preserve existing shell and tmux compatibility while adding persistence under the new orchestration seam rather than rewriting startup flow.

### Implementation Guardrails

- Do not implement task assignment, worker registration, or recovery orchestration in this story.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]
- Do not let `events.ndjson` become the authority source; it is an export mirror of the authoritative SQLite event log.  
  [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
- Do not treat tmux pane state, adapter output, or shell wrapper files as canonical entity records.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Do not defer schema design so aggressively that Story 1.3 immediately has to rewrite it; include the architecture-named tables now, with nullable columns where later stories will fill in values.  
  [Inference from: _bmad-output/planning-artifacts/architecture.md#persistence-strategy and _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]
- Do not add third-party Python dependencies or a migration framework for this first persistence increment.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Open Questions Saved During Analysis

- Should the SQLite bootstrap use `PRAGMA journal_mode=WAL` for local durability and concurrent reads, or stay with the default journal mode until real multi-reader behavior is introduced? The architecture does not currently freeze this choice.
- Should event export append happen inside the same helper immediately after commit, or through a thin post-commit callback abstraction for future richer sinks? The architecture requires durable intent plus export, but not the exact internal layering.
- Should bootstrap create an empty `events.ndjson` eagerly for inspectability, or lazily on first event write? The acceptance criteria allow either, but Story 1.2 should choose one behavior and document it consistently.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/1-1-start-a-single-controller-orchestration-session.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/session.py`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/tests/test_setup_init.py`
- `tools/tmux_bridge/start_controller.sh`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Skill used: `bmad-create-story`
- Inputs loaded from the requested planning artifacts, sprint tracking, Story 1.1 artifact, and current brownfield bootstrap code

### Completion Notes List

- Implemented the authoritative persistence layer in [`tools/orchestration/store.py`](/home/codexuser/macs_dev/tools/orchestration/store.py) with SQLite schema bootstrap for the controller-owned entity tables plus supporting audit and recovery tables.
- Extended the existing bootstrap seam so `macs setup init` now creates or verifies `.codex/orchestration/state.db` and `.codex/orchestration/events.ndjson` without introducing a second controller-authority path.
- Added a transactional write helper that commits canonical SQLite rows before mirroring the authoritative event to `events.ndjson`.
- Added stdlib regression coverage for schema bootstrap, JSON output status, successful SQLite-plus-NDJSON writes, rollback behavior, and preserved launcher compatibility.
- Verified the implementation with `python3 -m unittest discover -s tools/orchestration/tests` and `./tools/tmux_bridge/tests/smoke.sh`.

### File List

- `_bmad-output/implementation-artifacts/stories/1-2-persist-authoritative-control-plane-entities.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/session.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_setup_init.py`
