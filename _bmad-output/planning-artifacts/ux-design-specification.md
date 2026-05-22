---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-03-core-experience
  - step-04-emotional-response
  - step-05-inspiration
  - step-06-design-system
  - step-07-defining-experience
  - step-08-visual-foundation
  - step-09-design-directions
  - step-10-user-journeys
  - step-11-component-strategy
  - step-12-ux-patterns
  - step-13-responsive-accessibility
  - step-14-complete
inputDocuments:
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/prd.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev.md
  - /home/codexuser/macs_dev/_bmad-output/project-context.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/macs-multi-agent-orchestration-diagram-pack-2026-04-09.md
  - /home/codexuser/macs_dev/_bmad-output/planning-artifacts/research/domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md
workflowType: ux-design
lastStep: 14
status: complete
---

# UX Design Specification macs_dev

**Author:** Dicky  
**Date:** 2026-04-09T19:00:00+01:00

---

## Executive Summary

### Project Vision

MACS Phase 1 should feel like a trustworthy local control room for parallel agent work, not a pile of tmux panes the operator has to mentally reconcile. The UX goal is a CLI/tmux-native orchestration surface where the maintainer can discover workers, inspect evidence, assign work, understand ownership and locks, intervene during degraded sessions, and recover cleanly without abandoning the product for manual shell surgery.

The experience must preserve the product's core governance promise from the PRD: the controller owns truth for `worker`, `task`, `lease`, `lock`, and `event`, while runtime adapters provide bounded evidence instead of authority. UX decisions therefore need to make state authority legible, keep intervention close to the active workflow, and expose recovery paths before ambiguity becomes damage.

### Target Users

Primary operators are maintainers already comfortable with shell, tmux, repo-local tooling, and mixed AI runtimes. They are not looking for a glossy dashboard. They want dense, inspectable information, fast keyboard-driven actions, predictable terminology, and the ability to move from summary to raw evidence without losing context.

Secondary users are serious adopters bringing MACS into real repositories. They need setup, worker registration, policy defaults, and safe operating guidance to be understandable without bespoke glue code or deep reverse-engineering of internal state.

Tertiary users are contributors extending adapters and orchestration behavior. For them, UX includes contributor-facing commands, docs, validation outputs, and inspection tools that explain how a new runtime becomes a governed worker rather than an opaque plugin.

### Key Design Challenges

- The CLI/tmux surface must show high-signal orchestration state without collapsing into noisy terminal telemetry.
- Worker health, freshness, capability, and token/session evidence vary by adapter; the UI must present absence and uncertainty explicitly rather than flattening everything into false precision.
- Recovery flows must stop split-brain behavior while still letting operators act quickly under pressure.
- Lock and ownership state must be understandable at a glance even when several workers are active in parallel.
- Setup and adapter registration must feel conservative and safe, not magical or under-specified.

### Design Opportunities

- Turn tmux into an advantage by making panes part of a governed operational workspace rather than an implementation detail.
- Make evidence-backed routing visible enough that operators trust the controller's decisions and can challenge them when needed.
- Use consistent control-plane language everywhere so the product teaches its model through use.
- Create contributor flows that turn adapter work into a repeatable contract-and-validation process instead of tribal knowledge.

## Core User Experience

### Defining Experience

The defining experience is: an operator can stand in one controller pane, see the state of a live multi-worker session, issue a task assignment, and immediately understand who owns the task, what surfaces are locked, why that worker was chosen, and what intervention options remain available if conditions degrade.

This is not a "chat with agents" UX. It is an orchestration UX. The unit of value is governed coordination under load. The product feels successful when the operator never has to infer critical state from memory or by reading multiple raw panes side by side.

### Platform Strategy

The primary surface is a local-host CLI paired with tmux windows or panes. The CLI is the authority surface for summaries, actions, inspection, and replayable history; tmux is the live execution surface for worker sessions. The CLI should assume keyboard-first operation, monospaced layouts, narrow and wide terminal support, and direct interoperability with existing MACS shell-first workflows.

There is no requirement for a web UI in Phase 1. Any richer status composition should still render inside terminal workflows through tables, inspectors, side panels, overlays, or split-pane conventions that remain scriptable and SSH-friendly.

### Effortless Interactions

These interactions must feel immediate and low-friction:

- discovering the current worker roster and understanding readiness
- assigning a task with scope, target policy, and visible routing rationale
- checking current owner, lease state, and protected-surface locks
- opening the right worker pane from a task or worker record
- pausing, aborting, rerouting, or reconciling from the same inspection path
- moving from alert to evidence to action in one flow

The CLI should remove bookkeeping steps, not hide decisions. "Effortless" means fewer mental joins, fewer context switches, and fewer commands needed to answer common operational questions.

### Critical Success Moments

The first critical success moment is the first parallel assignment: after dispatching work, the operator sees a clear owner, lease, lock reservation, and event entry without reading raw worker output.

The second is the first degraded-state intervention: the controller warns early, freezes unsafe continuation semantics, and lets the operator inspect and reroute without manual tmux rescue work.

The third is setup completion: a new adopter registers mixed runtimes, validates them, and reaches a safe ready state without repository-specific hacking.

### Experience Principles

- Controller first: authoritative state appears before adapter detail.
- Evidence over vibes: every status badge that matters should be explainable.
- Dense but calm: terminal views can be information-rich without becoming visually chaotic.
- Intervention in place: operators should act from the current context, not hunt for separate recovery commands.
- Explicit uncertainty: missing, stale, or weak signals are shown as such.
- Safe defaults: dangerous actions require deliberate confirmation and clear consequence framing.

## Desired Emotional Response

### Primary Emotional Goals

Operators should feel oriented, in control, and appropriately skeptical. The experience should reduce the anxiety common in multi-agent work where several sessions are active but ownership is unclear.

The target emotional profile is:

- calm confidence during normal orchestration
- productive urgency during degraded sessions
- trust in the audit trail after failures
- low ambiguity during setup and extension work

### Emotional Journey Mapping

Before dispatch, the operator should feel that the controller understands the playing field. During execution, they should feel that the system is watching for them, not merely displaying logs. During intervention, they should feel supported by structure rather than thrown into a forensic scramble. After recovery, they should feel that the history is preserved well enough to explain what happened.

### Micro-Emotions

- reassurance when assignment shows a single current owner and explicit lock creation
- healthy skepticism when the UI marks adapter signals as stale, partial, or unverified
- controlled urgency when degraded state becomes visible with a recommended next action
- closure when recovery preserves old and new lease history instead of overwriting it

### Design Implications

The interface should not anthropomorphize workers or lean on decorative delight. Its emotional quality comes from clarity, pacing, and consequence framing. Warnings should be crisp, not dramatic. Recovery flows should feel procedural and dependable, not improvisational.

### Emotional Design Principles

- Prefer composure over animation-heavy urgency.
- Use visual emphasis to clarify risk, not to entertain.
- Make irreversible actions feel weighty.
- Reward understanding with good inspection tools rather than hiding complexity.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

The most relevant inspiration is not consumer UI. It comes from operational terminal tools and infrastructure consoles: `git` for explicit state transitions, `kubectl` and `systemctl` for inspectable object state, `htop` for glanceable density, and tmux itself for spatial awareness. The UX should borrow the best qualities of these tools: compact summaries, drill-down detail, predictable verbs, and low-latency keyboard flow.

The research also suggests alignment with modern orchestration systems that separate control plane from execution plane. The MACS UX should reflect that separation directly: controller views resemble a ledger and scheduler; worker panes remain execution contexts.

### Transferable UX Patterns

- object-oriented CLI nouns: `worker`, `task`, `lease`, `lock`, `event`, `adapter`
- summary-to-detail layering: roster view to record inspector to raw evidence
- state badges with confidence/freshness qualifiers
- timeline inspection for post-failure understanding
- dry-run and validation output for setup and contributor actions

### Anti-Patterns to Avoid

- generic chatbot framing that makes orchestration state secondary
- hidden automatic rerouting or silent ownership transfer
- ambiguous labels like "active" when the real state is degraded or expiring
- raw tmux pane dependence for answering canonical controller questions
- over-designed pseudo-dashboard visuals that do not survive narrow terminal widths

### Design Inspiration Strategy

Use terminal-native patterns first, then selectively introduce richer structural affordances such as bordered inspectors, split sections, inline action hints, and compact severity color coding. The goal is "operations-grade terminal UX," not an imitation GUI rendered in ASCII.

## Design System Foundation

### 1.1 Design System Choice

The design system should be custom and terminal-native rather than borrowed from a browser component library. It should define:

- canonical nouns and verbs
- severity color roles
- spacing rhythm for command output and inspectors
- table/list conventions
- badge/state label grammar
- confirmation and escalation patterns

### Rationale for Selection

Phase 1 lives in CLI and tmux. Traditional web design systems solve the wrong constraints. MACS needs a system for terminal composition, status semantics, and operator decision support. The system should privilege scanability, terminal compatibility, color fallback behavior, and scriptable output modes.

### Implementation Approach

Design the UX as a layered terminal system:

- default compact command output for routine use
- enhanced interactive inspector views for deep investigation
- optional machine-readable output modes for automation and tests

Each human-facing command should produce stable layouts with predictable columns and labels so operators can build muscle memory quickly.

### Customization Strategy

Support at least two visual modes:

- standard color mode for modern terminals
- reduced-color/high-contrast mode for accessibility and low-fidelity environments

Allow operators to configure density and timestamp verbosity, but do not let customization change control-plane terminology or state semantics.

## 2. Core User Experience

### 2.1 Defining Experience

The product should make one controller pane feel like the source of operational truth for a multi-pane system. The operator's mental model is "I am governing a fleet from here," not "I am chasing several independent sessions."

### 2.2 User Mental Model

The UX should teach this mental model:

- a `worker` is a governed execution endpoint backed by a runtime adapter and a tmux session
- a `task` is a controller-tracked unit of work with scope and intent
- a `lease` is the current ownership grant for a task
- a `lock` reserves protected surfaces against unsafe overlap
- an `event` is the durable explanation of what happened
- an `adapter` is evidence-bearing infrastructure, not decision-making authority

This model needs to be restated through command naming, inspection layouts, docs, and warning text until it becomes second nature.

### 2.3 Success Criteria

The UX succeeds when operators can answer these questions in under a few seconds:

- Which workers are available, degraded, or quarantined?
- Who currently owns task `X`?
- Which surfaces are locked and why?
- Why was this worker selected or rejected?
- What changed in the last few minutes?
- What is the safest next action right now?

### 2.4 Novel UX Patterns

MACS should introduce a few distinctive patterns:

- lease-centric task inspection, where current owner and ownership history are primary fields
- lock overlays that can be viewed from either task or surface perspective
- evidence stacks that separate controller facts, adapter signals, and untrusted claims
- degraded-session intervention panels with recommended actions and freeze semantics

### 2.5 Experience Mechanics

Core mechanics for the operator surface:

- roster mechanics: rank workers by eligibility and risk, not alphabetically alone
- dispatch mechanics: show policy, capability fit, conflicts, and assignment result in one output
- inspection mechanics: every summary item can expand into history and raw evidence
- intervention mechanics: pause, resume, reroute, reconcile, and abort share a common pattern
- recovery mechanics: preserve old state, propose next state, require explicit acceptance for transfers

## Visual Design Foundation

### Color System

The terminal palette should be restrained and semantic:

- base foreground/background: neutral, low-glare, high-contrast
- healthy/ready: muted green
- warning/degraded: amber
- unsafe/quarantined/conflict: red
- informational/controller authority: cyan or blue
- unverified/claim-only: dim neutral or violet-gray accent

Color must reinforce state but never be the only signal. Every severity color needs a textual label and icon/marker fallback such as `READY`, `DEGRADED`, `CONFLICT`, `QUARANTINED`.

### Typography System

Typography is terminal-constrained, so the system should rely on hierarchy through casing, spacing, and alignment:

- command outputs use sentence case labels and monospace tabular alignment
- primary headings in interactive views use uppercase or strong box titles sparingly
- identifiers like task IDs, lease IDs, pane IDs, and adapter names are always monospace literals
- changed fields or critical evidence should align in key-value blocks rather than prose dumps

### Spacing & Layout Foundation

Use a consistent spatial model:

- top summary strip for scope and current object
- main body for dense state rows
- right or lower detail region for evidence/history when space permits
- action footer with keyboard hints and safe next actions

On narrow terminals, stack these regions vertically in the same order.

### Accessibility Considerations

Never assume full color perception or wide screens. Ensure readable contrast, stable keyboard-only flow, no blinking alerts, and concise language. Critical alerts should remain understandable in plain-text logs or pasted output without styling.

## Design Direction Decision

### Design Directions Explored

Three candidate directions fit the product:

- Command Ledger: sober, text-dense, audit-first
- Control Room: structured, pane-aware, operationally visual
- Guided Ops: more assistive, recommendation-heavy, lower-density

### Chosen Direction

Choose **Control Room** with **Command Ledger** discipline.

That means the primary experience is an operational console with strong structure, visible live state, and pane awareness, while preserving the explicitness and auditability of infrastructure tooling. Avoid the hand-holding tone of Guided Ops except during onboarding and recovery suggestions.

### Design Rationale

The PRD's value proposition is legible orchestration under pressure. The Control Room direction best supports multi-worker awareness, lock visibility, and intervention. The Command Ledger influence ensures the UI remains precise, grep-friendly, and faithful to controller authority.

### Implementation Approach

Implement as a family of terminal views:

- command summaries for routine use
- watch/monitor modes for live operations
- focused inspectors for `worker`, `task`, `lease`, `lock`, and `event`
- guided wizards for setup, registration, and recovery checkpoints

## User Journey Flows

### Maintainer Runs a Successful Parallel Orchestration Session

1. Operator opens the controller session and lands on a roster/overview command or watch view.
2. The system shows workers with runtime, capability class, freshness, health, interruptibility, and budget/session evidence where available.
3. The operator creates or selects a task, specifies scope and protected surfaces, and requests assignment.
4. The controller evaluates eligibility, displays routing rationale, reserves locks, creates the lease, and records the event.
5. The operator sees the worker pane target, current owner, and lock state immediately.
6. The operator repeats for a second compatible task and monitors parallel progress without ambiguity.
7. Completed tasks move to closed state with preserved event history and released locks.

Success metric: the operator never needs raw pane output to answer ownership, routing, or lock questions.

### Maintainer Intervenes in a Degraded Session

1. The monitor view surfaces a worker as `DEGRADED` or `UNSAFE` with evidence summary.
2. The operator opens the task or worker inspector and sees current lease, recent events, protected surfaces, and freshness details.
3. The operator issues `pause` or an equivalent in-context action.
4. The controller freezes risky continuation, logs the intervention, and blocks unsafe competing ownership.
5. The operator chooses resume, reroute, reconcile, or abort based on the evidence panel.
6. If rerouting, the new lease is created only after the old one is explicitly superseded or revoked.
7. The event trail preserves both the anomaly and the operator rationale.

Success metric: intervention takes one guided flow, not ad hoc tmux operations.

### Adopter Setup and Onboarding

1. New adopter runs MACS setup in a repository.
2. The onboarding flow detects tmux readiness, repo-local state paths, and default runtime availability.
3. The user is guided through controller defaults, safety policies, and adapter registration in a conservative order.
4. Each adapter is validated against the minimum contract and reported as ready, partial, degraded-capable, or invalid.
5. The user reviews the worker roster and policy defaults before running the first live session.
6. The product offers a sample mixed-runtime orchestration scenario and a safe dry-run path.

Success metric: a technically capable user reaches a four-worker local setup without undocumented glue code.

### Contributor Adapter Flow

1. Contributor opens the adapter guide and scaffold or inspect command.
2. The system shows the minimum adapter contract, required signals, optional enrichments, and degradation rules.
3. The contributor registers or updates the adapter manifest and test configuration.
4. Validation tools show which contract fields are satisfied, missing, stale, or semantically weak.
5. The contributor runs the regression harness and reviews behavior in healthy and degraded scenarios.
6. Only then is the adapter promoted toward first-class support.

Success metric: adapter UX behaves like a governed extension workflow, not a plugin free-for-all.

### Journey Patterns

- Every journey starts from authoritative controller state.
- Every risky action is paired with a visible consequence summary.
- Every object can be inspected from summary to history to raw evidence.
- Every recovery path preserves prior state instead of rewriting history.

### Flow Optimization Principles

- Keep normal-path commands short and memorable.
- Put the most likely next action in the current view footer.
- Offer drill-down before requiring freeform investigation.
- Prefer explicit state changes over hidden automation.

## Component Strategy

### Design System Components

Core terminal components:

- overview header
- worker roster table
- task queue table
- lease inspector
- lock map / lock list
- event timeline
- alert strip
- action footer
- confirmation dialog/prompt
- setup wizard stepper
- validation result panel

These should be reusable across command modes so the user sees the same semantics whether in a summary command, watch mode, or interactive inspector.

### Custom Components

Custom components required for MACS:

`Evidence Stack`
Presents controller facts, adapter signals, and untrusted claims as separate grouped sections with freshness timestamps and confidence labels.

`Lease Transfer Panel`
Shows current owner, transfer candidate, required preconditions, and resulting lock changes before reroute or reconciliation completes.

`Protected Surface Map`
Displays reserved, blocked, conflicted, and free surfaces, grouped by file path, directory, module, or declared work surface.

`Degraded Session Panel`
Summarizes anomaly type, last good evidence, current risk classification, recommended actions, and whether freeze semantics are active.

`Adapter Contract Validator`
Shows required contract fields, optional enrichments, degradation behavior, validation status, and failing test links.

### Component Implementation Strategy

Build components around a single state vocabulary shared with the controller model. Avoid view-specific aliases for the same concept. Every component should support:

- compact mode for command output
- expanded mode for detailed inspection
- deterministic text rendering for tests and documentation

### Implementation Roadmap

Phase 1:

- worker roster
- task/lease inspector
- lock inspector
- event timeline
- assignment result view
- degraded session panel

Phase 2:

- onboarding/setup wizard
- adapter contract validator
- protected surface map
- recovery/reconciliation wizard

Phase 3:

- richer watch dashboards
- comparative routing inspector
- post-run analysis bundles

## UX Consistency Patterns

### Button Hierarchy

Because this is CLI-first, "button hierarchy" maps to action hierarchy:

- primary actions: `assign`, `inspect`, `pause`, `reroute`, `recover`
- secondary actions: `open-pane`, `show-events`, `show-locks`, `show-evidence`
- destructive actions: `abort`, `revoke-lease`, `quarantine`

Primary actions should appear inline in current context. Destructive actions require confirmation with consequence text and affected objects listed.

### Feedback Patterns

- Success: concise confirmation plus changed state summary.
- Warning: explain what is uncertain or degraded and what the operator can do next.
- Error: show the failed operation, the reason, and whether controller state changed.
- Info: use for supplemental evidence, not for operationally important state.

Every intervention and routing action should emit a human-readable result and an event ID reference.

### Form Patterns

Task creation, setup, and adapter registration should prefer structured prompts with defaults, inline validation, and preview output. Freeform text should be allowed where task intent needs it, but protected surfaces, runtime choice, and policy fields should be constrained and inspectable.

Validation rules should run before commit, especially for:

- missing scope
- conflicting locks
- unsupported adapter capabilities
- unsafe recovery preconditions

### Navigation Patterns

Navigation should be object-first:

- global overview
- worker detail
- task detail
- lease detail
- lock detail
- event detail
- adapter detail

Operators should move between linked objects with consistent verbs such as `inspect`, `show`, `open`, and `trace`.

### Additional Patterns

Alert pattern:
Alert rows must include severity, affected object, reason, freshness, and next suggested action.

Timeline pattern:
Event history should sort newest first by default, with filters for object, severity, and intervention class.

Lock conflict pattern:
Whenever a task is blocked by a lock, show the blocking owner, lease age, protected surface, and the safe resolution options.

Absence pattern:
Missing adapter signals should render as `UNAVAILABLE` or `NOT EXPOSED`, never as zero values.

## Responsive Design & Accessibility

### Responsive Strategy

Phase 1 responsiveness is terminal responsiveness. The design must adapt to:

- narrow laptop terminals
- half-width tmux panes
- full-width desktop terminals
- remote SSH sessions with inconsistent color support

On wide layouts, present summary and detail in adjacent regions. On narrow layouts, switch to stacked sections with collapsible detail groups and shorter column sets.

### Breakpoint Strategy

Recommended terminal breakpoints:

- narrow: under 100 columns
- standard: 100 to 159 columns
- wide: 160 columns and above

At narrow widths, prioritize current object, state, owner, and next action. At standard widths, add evidence summaries and secondary metadata. At wide widths, show side-by-side inspectors and richer timelines.

### Accessibility Strategy

Target WCAG AA-equivalent principles within terminal constraints:

- never depend on color alone
- preserve strong contrast in default themes
- keep command names and labels readable in screen readers
- support full keyboard operation with minimal mode switching
- avoid overloaded abbreviations for critical concepts
- provide reduced-motion/no-flash behavior by default

Documentation and examples should include plain-text output samples so users relying on assistive tooling can learn the interface model.

### Testing Strategy

UX verification should include:

- narrow and wide terminal snapshots
- color-disabled and high-contrast runs
- keyboard-only walkthroughs for setup, assignment, intervention, and recovery
- screen-reader spot checks on interactive terminal flows where feasible
- degraded-state drills to ensure warnings remain understandable under stress

Also test copy-paste durability: critical outputs should remain understandable when pasted into issues, docs, or chat.

### Implementation Guidelines

- Keep terminology exactly aligned with the PRD entities.
- Prefer stable key-value sections and tables over prose-heavy output.
- Render freshness and confidence explicitly.
- Make every destructive flow confirm both target and consequence.
- Support machine-readable output for every major inspection surface.
- Treat setup, recovery, and contributor validation as first-class UX, not documentation leftovers.

## Operator Surface Blueprint

### Primary CLI Areas

The Phase 1 operator surface should organize around these command families:

- `macs overview`
- `macs workers`
- `macs tasks`
- `macs leases`
- `macs locks`
- `macs events`
- `macs assign`
- `macs intervene`
- `macs recover`
- `macs setup`
- `macs adapters`

These names are illustrative, but the object model should remain consistent even if final command names differ.

### tmux Workspace Model

The default tmux workspace should reserve:

- one controller pane/window for overview, commands, and inspectors
- one pane or window per active worker
- an optional event/watch pane for live anomalies and state changes

The controller surface should always tell the operator which pane/window corresponds to a worker and provide a direct open/jump action.

### Recommended Default Views

Default overview content:

- active alerts
- worker summary counts by state
- active task summary with current owner
- current lock conflicts or holds
- recent intervention/recovery events

Default worker row fields:

- worker ID
- runtime/adapter
- state
- capability profile
- freshness
- interruptibility
- budget/session signal
- current lease count
- pane target

Default task row fields:

- task ID
- summary
- owner
- lease state
- lock footprint
- health/risk
- last event time

## Setup and Onboarding Specification

### Onboarding Goals

Setup should prove three things before first real orchestration:

- the environment is valid
- the workers are governable
- the operator understands the safety model

### Onboarding Sequence

1. Environment checks: tmux, repo-local paths, shell compatibility, runtime availability.
2. Controller defaults: choose or confirm controller runtime, state paths, and safety defaults.
3. Adapter registration: discover installed runtimes and walk the user through explicit enablement.
4. Validation: test required adapter contract signals and degraded behavior reporting.
5. Policy review: show workflow-class defaults, trust boundaries, and no-auto-push safeguards.
6. Dry run: simulate worker discovery and assignment without risking real work.
7. First live task: recommend a small sample orchestration scenario.

### Onboarding UX Requirements

- show what was auto-detected versus what the user explicitly approved
- preserve partial progress so setup can resume
- never silently register a worker as first-class without validation
- explain why an adapter is partial or degraded-capable rather than simply "failed"

## Worker Discovery and Registration Specification

### Discovery Model

Discovery must distinguish:

- discovered but unregistered workers
- registered but currently unavailable workers
- healthy eligible workers
- degraded workers
- quarantined workers

Discovery output should clearly separate presence from eligibility.

### Registration Flow

Registration should collect:

- worker identity
- runtime/adapter type
- declared capabilities
- required signal support
- optional enrichment support
- degraded behavior rules
- pane/session binding strategy

The final confirmation screen should show how the controller will interpret this worker, including any capability or signal caveats.

## Task Assignment Specification

### Assignment Interaction

Assignment is a structured flow, not a blind send:

1. select or define task intent
2. define protected surfaces or scope hints
3. review eligible workers and disqualifiers
4. inspect routing rationale
5. confirm lease and lock effects
6. dispatch and observe acknowledgment

### Assignment Result Requirements

The result view must show:

- assigned worker
- created lease ID
- reserved locks
- routing evidence summary
- event record created
- pane or session target
- immediate next action options

## Ownership and Lock Inspection Specification

### Ownership View

Ownership inspection should answer:

- who owns the task now
- how long the lease has been active
- what previous owners existed
- whether ownership is stable, expiring, held, or under reconciliation

### Lock View

Lock inspection should support both:

- task-first view: what this task currently holds or needs
- surface-first view: which task/lease currently blocks this surface

Historical lock changes must remain visible for post-run analysis.

## Degraded Session Intervention Specification

### Degradation States

Minimum operator-visible states:

- healthy
- degraded
- unsafe
- unavailable
- quarantined

Each state should show its basis: freshness, liveness, adapter health, budget/session evidence, conflicting claims, or recovery interruption.

### Intervention Flow

From any degraded state, the operator should be able to:

- inspect evidence
- pause current progression
- checkpoint if supported
- reroute to an alternate worker
- quarantine the worker
- abort the task
- start reconciliation

The system should recommend actions but never auto-execute high-consequence interventions without operator approval.

## Recovery and Reconciliation Specification

### Recovery Principles

Recovery must assume external side effects are not atomically reversible. Therefore the UX needs to emphasize:

- preserving history
- freezing ambiguous ownership
- comparing old and proposed new state
- forcing explicit acceptance before resuming execution

### Reconciliation Flow

1. anomaly detection and freeze
2. evidence review
3. choose recovery path: resume, reroute, reconcile, abort
4. compare resulting ownership and lock changes
5. execute and log rationale
6. verify single current owner after completion

### Post-Recovery UX

After recovery, the operator should see a compact summary of:

- prior lease
- new lease or final disposition
- lock changes
- affected workers
- event trail continuity

## Contributor Adapter Flow Specification

### Contributor Experience Goals

Contributor UX should make the adapter model explicit enough that extending MACS feels constrained in a good way. The contributor should know what is mandatory, what is optional, how degradation is represented, and how validation determines readiness.

### Contributor Workflow

1. inspect contract
2. scaffold or update adapter metadata
3. implement required surfaces
4. declare optional enrichments
5. specify degradation behavior
6. run validation and regression tests
7. inspect failures by contract area and scenario

### Contributor UX Requirements

- show contract expectations in the same nouns used by the operator UX
- map failing tests to user-visible orchestration consequences
- distinguish unsupported from incorrectly implemented
- provide sample outputs for healthy, degraded, and unavailable states

## Open Questions and Follow-On Artifacts

### Open Questions

- Should watch mode prioritize global orchestration health or the operator's currently selected objects?
- How much interactive TUI behavior is appropriate in Phase 1 versus plain command output plus tmux conventions?
- What degree of semantic protected-surface modeling is feasible before lock UX becomes overcomplicated?
- Which setup steps can be safely auto-detected without reducing operator trust?

### Recommended Next Artifacts

- command inventory and IA for the operator CLI
- wireframes for overview, worker inspector, task/lease inspector, degraded panel, and recovery flow
- example terminal snapshots for narrow and wide layouts
- copy deck for state labels, warnings, confirmations, and onboarding text
- contributor-facing adapter validation report template
