# Story 1.3: Enforce task and lease state invariants

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a maintainer,
I want explicit task and lease state machines with zero-or-one live lease enforcement,
so that ownership never becomes ambiguous during normal progression.

## Acceptance Criteria

1. Given a task with an existing live lease, when the controller evaluates a lease mutation or ownership transfer, then it allows only one live lease state for that task at any time, and it records revoked, expired, completed, and replaced leases as historical records rather than active ownership.  
   [Source: _bmad-output/planning-artifacts/epics.md#story-13-enforce-task-and-lease-state-invariants]
2. Controller-authoritative `task.state` and `lease.state` values match the canonical vocabularies and transition rules frozen in the Phase 1 architecture and operator CLI contract, so later CLI, recovery, and inspection stories consume one consistent state model.  
   [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies]
3. Authoritative writes keep `tasks.current_worker_id` and `tasks.current_lease_id` aligned with task and lease lifecycle rules: `reserved` may point at a `pending_accept` lease, `active` requires a live lease, and historical or terminal lease states do not remain current ownership.  
   [Inference from: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model, _bmad-output/planning-artifacts/architecture.md#task-state-machine, and _bmad-output/planning-artifacts/architecture.md#lease-state-machine]
4. Invalid transitions or second-live-lease attempts fail closed without partial SQLite mutation or misleading `events.ndjson` export, preserving the Story 1.2 transaction boundary.  
   [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: tools/orchestration/store.py] [Source: tools/orchestration/tests/test_setup_init.py]

## Tasks / Subtasks

- [x] Codify canonical task and lease state machines in controller-owned Python helpers instead of scattering raw strings across store code and tests. (AC: 1, 2, 3)
  - [x] Add a focused helper module under `tools/orchestration/` for state vocabularies, live-lease classification, and allowed transition checks. Brownfield-safe options include `tools/orchestration/state_machine.py` or `tools/orchestration/task_lease.py`; do not rename the just-landed `tools/orchestration/store.py` seam unless the change is strictly mechanical and low risk.  
        [Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape] [Source: tools/orchestration/store.py]
  - [x] Encode the architecture-defined task transitions exactly: `draft -> pending_assignment -> reserved -> active`, `active -> intervention_hold|reconciliation|completed|failed`, `intervention_hold -> active|reconciliation`, `reconciliation -> reserved|failed`, and terminal archival transitions.  
        [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine]
  - [x] Encode the lease transitions and semantics exactly, including that `active`, `paused`, `suspended`, and `expiring` are live states; `pending_accept` is not live yet; and `revoked`, `expired`, `completed`, `failed`, and `replaced` are historical states.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model]
  - [x] Choose and lock one consistent rule for task pointer fields. Brownfield-safe default: a `reserved` task may reference the `pending_accept` lease and candidate worker, while only live lease states count as active ownership. Capture that rule in tests so later stories do not drift.  
        [Inference from: _bmad-output/planning-artifacts/architecture.md#task-state-machine and _bmad-output/planning-artifacts/architecture.md#lease-state-machine]

- [x] Strengthen `tools/orchestration/store.py` so SQLite helps enforce task and lease invariants instead of storing unconstrained state text. (AC: 1, 2, 3, 4)
  - [x] Add schema-level guardrails where SQLite can enforce them directly: canonical-state validation, foreign keys between `tasks`, `leases`, and `workers` where current schema supports them, and indexes needed for `current_lease_id` / task live-lease lookups.  
        [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-state-store] [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy] [Source: tools/orchestration/store.py]
  - [x] Enforce the zero-or-one live lease rule with a partial unique index on `leases(task_id)` for live states (`active`, `paused`, `suspended`, `expiring`) or an equivalent transactional constraint if SQLite limitations make a different mechanism safer.  
        [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-state-store] [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model] [Inference from: tools/orchestration/store.py]
  - [x] Update authoritative mutation helpers so lease-state changes atomically clear, retain, or supersede `tasks.current_lease_id` and `tasks.current_worker_id` as appropriate. Terminal task states must not retain live leases, and a successor lease must not become live until the predecessor is revoked or replaced.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
  - [x] Keep `write_eventful_transaction` as the authoritative commit boundary or wrap it with narrower helpers; invariant failures must abort before any NDJSON append occurs.  
        [Source: _bmad-output/planning-artifacts/architecture.md#write-model] [Source: tools/orchestration/store.py]

- [x] Add minimal internal task and lease mutation APIs that later stories can reuse without prematurely freezing public operator commands. (AC: 1, 3, 4)
  - [x] Provide internal helpers for the minimum transition set Story 1.3 must prove end-to-end: seed or create a task, attach a `pending_accept` lease, activate the lease, move a live lease to `paused`, `suspended`, `expiring`, `revoked`, `expired`, `completed`, or `failed`, and mark a revoked predecessor as `replaced` when a successor is activated.  
        [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/prd.md#technical-success]
  - [x] Keep `tools/orchestration/session.py` focused on repo/bootstrap responsibilities and keep `tools/orchestration/cli/main.py` thin. Story 1.3 should not turn into `macs task ...` or `macs lease ...` command work before Epic 4.  
        [Source: tools/orchestration/session.py] [Source: tools/orchestration/cli/main.py] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]
  - [x] If a test-only seed surface is needed, keep it internal to Python helpers or hidden test fixtures rather than exposing premature public verbs.  
        [Inference from: tools/orchestration/cli/main.py and _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]

- [x] Add explicit regression coverage for state-machine enforcement and ambiguous-ownership prevention. (AC: 1, 2, 3, 4)
  - [x] Add a dedicated stdlib `unittest` module such as `tools/orchestration/tests/test_task_lease_invariants.py` instead of overloading bootstrap tests with every transition case.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/project-context.md#testing-rules]
  - [x] Cover valid flows: `reserved + pending_accept`, `active + live lease`, `intervention_hold` with a paused or suspended live lease, and successor activation only after predecessor revocation or replacement.  
        [Source: _bmad-output/planning-artifacts/architecture.md#task-state-machine] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
  - [x] Cover invalid flows: second live lease for the same task, illegal direct transitions such as `draft -> active` or `active -> replaced`, terminal task states retaining live leases, and mismatched `current_lease_id` / `current_worker_id`.  
        [Source: _bmad-output/planning-artifacts/architecture.md#test-layers] [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies]
  - [x] Preserve Story 1.2 rollback guarantees by asserting failed invariant checks leave both SQLite rows and `events.ndjson` unchanged.  
        [Source: tools/orchestration/tests/test_setup_init.py] [Source: _bmad-output/planning-artifacts/architecture.md#write-model]

- [x] Keep brownfield compatibility and later Epic 1 work unblocked. (AC: 2, 3, 4)
  - [x] Preserve the existing Story 1.2 bootstrap contract in `macs setup init`, `tools/orchestration/session.py`, and `tools/orchestration/tests/test_setup_init.py`; Story 1.3 should extend the authoritative store seam, not reopen bootstrap design.  
        [Source: _bmad-output/implementation-artifacts/stories/1-2-persist-authoritative-control-plane-entities.md#completion-notes-list] [Source: tools/orchestration/session.py] [Source: tools/orchestration/tests/test_setup_init.py]
  - [x] Leave restart boot sequencing, routing, protected-surface locks, and public intervention flows to Stories 1.4, 3.x, and 5.x. This story supplies the shared invariants those later stories depend on, but it should not implement their command surfaces or recovery engines yet.  
        [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes] [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]
  - [x] Keep `tools/tmux_bridge/` transport-only and avoid introducing tmux dependencies into invariant tests. These semantics should be provable at the Python store layer.  
        [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/project-context.md#critical-implementation-rules]

## Dev Notes

### Story Intent

Story 1.3 turns the raw persistence foundation from Story 1.2 into controller-enforced task and lease semantics. It should establish the authoritative state vocabulary, allowed transitions, and live-lease guardrails that later routing, recovery, inspection, and intervention stories rely on, without prematurely implementing those broader workflows.  
[Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#sprint-1-control-plane-bootstrap-and-authority-foundation]

### Previous Story Intelligence

- Story 1.2 already landed the persistence seam in `tools/orchestration/store.py`, including schema bootstrap, `EventRecord`, and `write_eventful_transaction`.
- Story 1.2 also extended `macs setup init` and `tools/orchestration/session.py` so `.codex/orchestration/state.db` and `events.ndjson` already exist before Story 1.3 starts.
- Current tests prove bootstrap, JSON output, successful SQLite plus NDJSON commits, and rollback-without-export, but they do not yet prove any domain-specific task or lease invariants.
- The current schema includes `tasks.current_worker_id`, `tasks.current_lease_id`, and `leases.replacement_lease_id`, which gives Story 1.3 the right raw fields to enforce ownership semantics without inventing a parallel store.

[Source: _bmad-output/implementation-artifacts/stories/1-2-persist-authoritative-control-plane-entities.md#completion-notes-list]  
[Source: tools/orchestration/store.py]  
[Source: tools/orchestration/session.py]  
[Source: tools/orchestration/tests/test_setup_init.py]

### Brownfield Baseline

- The current public orchestration CLI surface is still only `macs setup init`.
- `tools/orchestration/` currently contains bootstrap, store, CLI, and tests, but no dedicated task or lease domain module yet.
- `tools/tmux_bridge/` remains the operational transport layer and should not absorb authoritative state-machine logic.
- The architecture's recommended module shape names `state_store.py`, but this repo's just-landed brownfield seam is `tools/orchestration/store.py`; extend the existing file unless a rename is truly low risk and mechanical.

[Source: tools/orchestration/cli/main.py]  
[Source: tools/orchestration/store.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]  
[Source: _bmad-output/project-context.md#critical-implementation-rules]

### Technical Requirements

- Use the canonical Phase 1 state vocabularies exactly:
  - `task.state`: `draft | pending_assignment | reserved | active | intervention_hold | reconciliation | completed | failed | aborted | archived`
  - `lease.state`: `pending_accept | active | paused | suspended | expiring | revoked | expired | completed | failed | replaced`
  [Source: _bmad-output/planning-artifacts/operator-cli-contract.md#canonical-state-vocabularies]
- Treat only `active`, `paused`, `suspended`, and `expiring` as live lease states. `pending_accept` reserves work but does not count as a live lease yet.  
  [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-domain-model] [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine]
- Preserve historical lease records. `revoked`, `expired`, `completed`, `failed`, and `replaced` must remain queryable history and must never be treated as current active ownership.  
  [Source: _bmad-output/planning-artifacts/epics.md#story-13-enforce-task-and-lease-state-invariants] [Source: _bmad-output/planning-artifacts/prd.md#technical-success]
- Keep authoritative writes transaction-safe and local-host-first under `.codex/orchestration/` using Python 3.8+ stdlib plus SQLite; do not add third-party Python dependencies or alternative storage layers.  
  [Source: _bmad-output/project-context.md#technology-stack--versions] [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy]
- Continue to treat `events.ndjson` as audit export, not authority. SQLite remains the canonical state store even when invariants fail or transitions are rejected.  
  [Source: _bmad-output/planning-artifacts/architecture.md#persistence-strategy] [Source: tools/orchestration/store.py]

### Architecture Compliance

- Only the controller can mutate task and lease state. Adapters and tmux observations remain evidence, not authoritative state transitions.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Controller actions must follow the write model: read authoritative state, validate invariants, write entity mutations and events in one transaction, then handle side effects or follow-up evidence explicitly.  
  [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- The authoritative store must support compare-and-swap style lease mutation and one-active-lease enforcement because restart recovery and failure containment later depend on those crisp invariants.  
  [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-state-store] [Source: _bmad-output/planning-artifacts/architecture.md#restart-recovery-and-reconciliation]
- Story 1.3 must preserve later semantics already frozen in the architecture: paused work remains live and blocks replacement unless revoked; successor activation cannot occur until the predecessor is clearly revoked or reconciled.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine] [Source: _bmad-output/planning-artifacts/ux-design-specification.md#maintainer-intervenes-in-a-degraded-session]
- Allow zero live leases where the product explicitly expects them, such as reconciliation, interrupted reassignment, or pre-acceptance reservation. Do not over-constrain the model so Story 1.4 or Epic 5 must immediately undo Story 1.3.  
  [Source: _bmad-output/planning-artifacts/prd.md#technical-success] [Inference from: _bmad-output/planning-artifacts/architecture.md#task-state-machine and _bmad-output/planning-artifacts/architecture.md#lease-state-machine]

### File Structure Requirements

- Extend the current authoritative store seam: `tools/orchestration/store.py`
- Keep repo/bootstrap responsibilities in: `tools/orchestration/session.py`
- Keep the current thin CLI entrypoint thin: `tools/orchestration/cli/main.py`
- Add new invariant/state-machine helpers under: `tools/orchestration/`
- Add focused invariant tests under: `tools/orchestration/tests/`
- Do not move invariant logic into `tools/tmux_bridge/`

[Source: tools/orchestration/store.py]  
[Source: tools/orchestration/session.py]  
[Source: tools/orchestration/cli/main.py]  
[Source: _bmad-output/planning-artifacts/architecture.md#recommended-module-shape]

### Testing Requirements

- Use `python3 -m unittest discover -s tools/orchestration/tests` as the primary validation surface for Story 1.3.  
  [Source: _bmad-output/implementation-artifacts/stories/1-2-persist-authoritative-control-plane-entities.md#testing-requirements]
- Prefer temp-repo SQLite tests over tmux-dependent tests for these invariants. Task and lease semantics should be provable without a live tmux server.  
  [Source: _bmad-output/project-context.md#testing-rules] [Source: tools/orchestration/tests/test_setup_init.py]
- Make state transitions explicit in tests: task state before and after, lease state before and after, current pointer alignment, event rows written, and NDJSON export behavior.  
  [Source: _bmad-output/project-context.md#testing-rules] [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]
- Cover the specific release-gate style invariant examples the architecture calls out: a task cannot hold two active leases, and a revoked predecessor lease is required before successor activation.  
  [Source: _bmad-output/planning-artifacts/architecture.md#test-layers]

### Git Intelligence Summary

Recent committed work is still narrow and compatibility-focused:

- `e474089` Add orchestration bootstrap and controller lock
- `19acf1e` Fix gitignore for local generated files
- `996c9f1` Merge pull request #10 from dickymoore/fix/tmux-target-pane-reliability
- `98912ea` Fix shellcheck source path
- `82d2c3a` Fix shellcheck sourcing hints

Implication for Story 1.3: keep the change as a targeted extension of the new orchestration seam and current shell compatibility, not a broad controller-surface rewrite.

### Implementation Guardrails

- Do not implement restart boot sequencing, recovery summaries, or live adapter probing in this story. Those belong to Story 1.4 and Epic 5.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#recommended-first-story-queue]
- Do not expose public `macs task ...` or `macs lease ...` verbs yet. Story 1.3 is about authoritative semantics, not the finished operator surface.  
  [Source: _bmad-output/planning-artifacts/sprint-plan-2026-04-09.md#dependency-notes]
- Do not let tmux observations, adapter outputs, or shell wrapper files mutate task or lease authority directly.  
  [Source: _bmad-output/planning-artifacts/architecture.md#state-authority-rules]
- Do not treat paused or suspended leases as historical. They remain live and must block replacement until revoked.  
  [Source: _bmad-output/planning-artifacts/architecture.md#lease-state-machine]
- Do not allow a second live lease to become authoritative through ad hoc SQL or direct table writes that bypass controller validation.  
  [Source: _bmad-output/planning-artifacts/architecture.md#authoritative-state-store] [Source: _bmad-output/planning-artifacts/architecture.md#write-model]
- Do not add a migration framework, ORM, or third-party dependency for this increment.  
  [Source: _bmad-output/project-context.md#technology-stack--versions]

### Project Structure Notes

- This remains a brownfield, shell-first repo. The authoritative control-plane code is only beginning to accumulate under `tools/orchestration/`.
- Story 1.2 already established the correct seam. Story 1.3 should deepen that seam with explicit invariant logic rather than inventing a parallel controller path.
- A small dedicated invariant module is appropriate here, but the public repo shape should still feel incremental and familiar to the existing tmux-bridge workflow.

### References

- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/operator-cli-contract.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/sprint-plan-2026-04-09.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/stories/1-2-persist-authoritative-control-plane-entities.md`
- `README.md`
- `docs/getting-started.md`
- `tools/orchestration/cli/main.py`
- `tools/orchestration/session.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_setup_init.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Skill used: `bmad-create-story`
- Inputs loaded from the requested planning artifacts, sprint tracking file, Story 1.2 artifact, and the current `tools/orchestration/` persistence seam

### Completion Notes List

- Added controller-owned task and lease state-machine helpers so canonical vocabularies, live-lease classification, and transition rules are enforced in one place.
- Strengthened the SQLite schema and invariant layer to reject invalid states, block a second live lease, and keep task ownership pointers aligned with lease lifecycle rules.
- Added regression coverage proving reserved plus pending-accept ownership, successor-lease gating, invalid transition rejection, terminal-task cleanup, and no-NDJSON-on-failed-transaction behavior.

### File List

- `_bmad-output/implementation-artifacts/stories/1-3-enforce-task-and-lease-state-invariants.md`
- `tools/orchestration/invariants.py`
- `tools/orchestration/state_machine.py`
- `tools/orchestration/store.py`
- `tools/orchestration/tests/test_setup_init.py`
