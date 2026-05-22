# MACS Phase 1 Operator CLI Contract

## Purpose

This artifact freezes the Phase 1 operator CLI contract for the controller-owned orchestration surface.

It is based on:

- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/ux-design-specification.md`
- `_bmad-output/planning-artifacts/epics.md`
- `.source/deep-research-report.md`
- `.source/deep-research-report (1).md`

Where the planning set is suggestive rather than explicit, this document makes conservative Phase 1 assumptions and marks them as contract decisions.

## Contract Decisions

- Canonical command shape: `macs <family> <verb> [selector] [flags]`
- Canonical object nouns: `worker`, `task`, `lease`, `lock`, `event`, `adapter`
- Utility families: `overview`, `recovery`, `setup`
- Canonical family names use singular object nouns:
  - `macs worker`
  - `macs task`
  - `macs lease`
  - `macs lock`
  - `macs event`
  - `macs adapter`
- `overview`, `setup`, and `recovery` are top-level families because the UX planning set requires them, even though they are not domain objects.
- Contract decision: plural family spellings from UX drafts, such as `macs workers` or `macs tasks`, may exist as compatibility aliases, but they are not the canonical Phase 1 documentation surface.

## Global Rules

- Default output is human-readable.
- Every list, inspect, validation, and lifecycle command in this contract must support `--json`.
- Human-readable output must show controller truth before adapter evidence.
- Degraded or missing signals must be labeled explicitly.
- Normal operations must not require raw tmux commands.
- High-consequence actions remain operator-confirmed even if the command is non-interactive.

## Command Families

| Family | Primary verbs frozen for Phase 1 | Notes |
|---|---|---|
| `overview` | `show`, `watch` | Global controller summary surface |
| `worker` | `list`, `discover`, `inspect`, `register`, `enable`, `disable`, `quarantine` | Worker discovery and governability |
| `task` | `list`, `create`, `assign`, `inspect`, `pause`, `resume`, `reroute`, `abort`, `close`, `archive` | Normal orchestration path |
| `lease` | `inspect`, `history` | Ownership truth and history |
| `lock` | `list`, `inspect`, `override`, `release` | Protected-surface visibility and exceptions |
| `event` | `list`, `inspect`, `tail`, `export` | Audit and live anomaly stream |
| `adapter` | `list`, `inspect`, `probe`, `validate` | Adapter contract and capability depth |
| `recovery` | `inspect`, `reconcile`, `retry` | Recovery and reconciliation flows |
| `setup` | `check`, `init`, `validate`, `dry-run` | Onboarding and qualification |

## Minimum Required Flags

These are the minimum required flags or selectors. Commands may accept more flags, but Phase 1 docs and examples must not rely on hidden required inputs beyond these.

| Command | Minimum required flags |
|---|---|
| `macs overview show` | none |
| `macs overview watch` | none |
| `macs worker list` | none |
| `macs worker discover` | none |
| `macs worker inspect` | `--worker <worker-id>` |
| `macs worker register` | `--adapter <adapter-id>` `--worker <worker-id>` |
| `macs worker enable` | `--worker <worker-id>` |
| `macs worker disable` | `--worker <worker-id>` |
| `macs worker quarantine` | `--worker <worker-id>` |
| `macs task list` | none |
| `macs task create` | `--summary <text>` |
| `macs task assign` | `--task <task-id>` and exactly one of `--worker <worker-id>` or `--workflow-class <class>` |
| `macs task inspect` | `--task <task-id>` |
| `macs task pause` | `--task <task-id>` |
| `macs task resume` | `--task <task-id>` |
| `macs task reroute` | `--task <task-id>` and either `--worker <worker-id>` or `--workflow-class <class>` |
| `macs task abort` | `--task <task-id>` |
| `macs task close` | `--task <task-id>` |
| `macs task archive` | `--task <task-id>` |
| `macs lease inspect` | `--lease <lease-id>` |
| `macs lease history` | one of `--task <task-id>` or `--worker <worker-id>` |
| `macs lock list` | none |
| `macs lock inspect` | exactly one of `--lock <lock-id>` or `--surface <surface-ref>` |
| `macs lock override` | `--lock <lock-id>` |
| `macs lock release` | `--lock <lock-id>` |
| `macs event list` | none |
| `macs event inspect` | `--event <event-id>` |
| `macs event tail` | none |
| `macs event export` | none |
| `macs adapter list` | none |
| `macs adapter inspect` | `--adapter <adapter-id>` |
| `macs adapter probe` | one of `--adapter <adapter-id>` or `--worker <worker-id>` |
| `macs adapter validate` | `--adapter <adapter-id>` |
| `macs recovery inspect` | `--task <task-id>` |
| `macs recovery reconcile` | `--task <task-id>` |
| `macs recovery retry` | `--task <task-id>` |
| `macs setup check` | none |
| `macs setup init` | none |
| `macs setup validate` | none |
| `macs setup dry-run` | none |

## Phase 1 Required Flags and Selectors

- `--json`: required on every command family in this contract.
- `--worker`, `--task`, `--lease`, `--lock`, `--event`, `--adapter`, `--surface`: canonical selectors.
- `--workflow-class`: canonical policy selector for routed assignment and reroute.
- Contract decision: `--surface` is required for write-impacting assignment only when the task does not already carry protected-surface metadata from `task create`.

## Required Human-Readable Output

### Shared output rules

- Output must stay compact, dense, and copy-paste durable.
- Use canonical nouns exactly: `worker`, `task`, `lease`, `lock`, `event`, `adapter`.
- Show warnings and degraded evidence inline, not only in verbose mode.
- For action commands, always print:
  - command result
  - primary affected object IDs
  - resulting state
  - event ID created
  - whether controller state changed
  - next recommended action when relevant

### Required list columns

| Surface | Required fields |
|---|---|
| `overview show` | active alerts, worker summary counts by state, active task summary with current owner, lock conflicts or holds, recent intervention or recovery events |
| `worker list` | worker ID, runtime or adapter, state, capability profile, freshness, interruptibility, budget or session signal, current lease count, pane target |
| `task list` | task ID, summary, owner, lease state, lock footprint, health or risk, last event time |
| `lock list` | lock ID, surface, state, task ID, lease ID, policy origin |
| `event list` | event ID, time, type, actor, object ref, severity or class |

### Required inspect content

| Command | Required content |
|---|---|
| `worker inspect` | controller truth, routability, freshness, interruptibility, adapter support depth, evidence basis, pane target |
| `task inspect` | task summary, state, current owner, current lease, lock summary, recent events, routing rationale summary |
| `lease inspect` | lease state, task ID, worker ID, started or updated times, replacement linkage, pause or suspension basis |
| `lock inspect` | surface, current holder, state, conflict status, related task and lease, history summary |
| `event inspect` | event type, actor, affected object refs, timestamps, payload summary, evidence refs if any |
| `adapter inspect` | supported operations, required signal status, unsupported features, degraded-mode behavior, qualification status |
| `recovery inspect` | anomaly summary, frozen objects, evidence layers, allowed next actions, comparison of current vs proposed state |

## Required `--json` Output

### JSON envelope

Every `--json` response must be valid JSON and use this top-level shape:

```json
{
  "ok": true,
  "command": "macs task inspect",
  "timestamp": "2026-04-09T19:00:00+01:00",
  "warnings": [],
  "errors": [],
  "data": {}
}
```

### JSON rules

- `ok` is `true` only when the requested command completed according to contract.
- `warnings` contains non-fatal issues such as degraded evidence or partial telemetry.
- `errors` contains structured errors when `ok` is `false`.
- `data` contains the command-specific payload.
- Contract decision: JSON keys use snake_case.

### Required JSON payload patterns

| Command type | Required `data` shape |
|---|---|
| list commands | `{"items":[...],"count":n}` |
| inspect commands | `{"object":{...}}` |
| action commands | `{"result":{...},"event":{...}}` |
| validation or probe commands | `{"status":{...},"checks":[...]}` |
| tail or watch commands | `{"items":[...],"cursor":"..."}` or stream of one-envelope-per-event records |

### Required object-state fields in JSON

- `worker` objects must include: `worker_id`, `adapter_id`, `runtime`, `state`, `freshness_seconds`, `interruptibility`, `required_signal_status`
- `task` objects must include: `task_id`, `summary`, `state`, `current_worker_id`, `current_lease_id`
- `lease` objects must include: `lease_id`, `task_id`, `worker_id`, `state`
- `lock` objects must include: `lock_id`, `surface_ref`, `task_id`, `lease_id`, `state`
- `event` objects must include: `event_id`, `event_type`, `actor_type`, `timestamp`

### Evidence JSON

Adapter-derived evidence included in `--json` outputs must preserve the common envelope from the architecture:

```json
{
  "adapter_id": "codex",
  "worker_id": "worker-codex-1",
  "observed_at": "2026-04-09T19:00:00+01:00",
  "kind": "fact|signal|claim",
  "name": "heartbeat|quota_warning|delivery_ack|capability_decl",
  "value": {},
  "freshness_seconds": 4,
  "confidence": "high|medium|low",
  "source_ref": "tmux:capture:%12"
}
```

## Status Conventions

### Canonical state vocabularies

- `worker.state`: `registered | ready | busy | degraded | unavailable | quarantined | retired`
- `task.state`: `draft | pending_assignment | reserved | active | intervention_hold | reconciliation | completed | failed | aborted | archived`
- `lease.state`: `pending_accept | active | paused | suspended | expiring | revoked | expired | completed | failed | replaced`
- `lock.state`: `reserved | active | released | overridden | conflicted`

### Human-readable status conventions

- Success lines must state the final controller-recognized state.
- Warning lines must state what is uncertain or degraded and what the operator can do next.
- Error lines must state:
  - attempted operation
  - reason
  - whether controller state changed
  - affected object IDs if known

### Exit codes

- `0`: success
- `2`: invalid input or missing required flags
- `3`: object not found
- `4`: policy blocked or state conflict
- `5`: degraded, unavailable, or unsupported precondition
- `6`: side effect failed after controller state transition to a safe explicit state
- `7`: timeout, missing acknowledgment, or incomplete live evidence

### Structured error codes

Phase 1 implementations should map errors into these stable codes:

- `invalid_argument`
- `not_found`
- `conflict`
- `policy_blocked`
- `unsupported`
- `degraded_precondition`
- `timeout`
- `side_effect_failed`
- `internal_error`

## Non-Goals for Phase 1

- No silent ownership transfer.
- No more than one live lease for a task.
- No cross-machine or hosted-control-plane dependency.
- No semantic merge intelligence beyond policy-defined protected surfaces.
- No adapter-driven authority mutation.
- No autonomous self-replanning outside controller-governed recovery flows.
- No requirement for a web UI.
- No requirement for a full-screen TUI; plain command output plus tmux navigation is sufficient.
- No guarantee of rich pause or resume semantics for every runtime; unsupported interventions must be explicit.

## Open but Frozen by Assumption

These choices are frozen for Phase 1 unless later planning artifacts supersede them:

- Singular family names are canonical.
- `overview`, `setup`, and `recovery` are first-class command families.
- `event export` may emit JSON or NDJSON, but `events.ndjson` remains the append-friendly audit export format on disk.
- `task assign` and `task reroute` accept either an explicit worker or a workflow-class policy selector as the minimum routing input.
