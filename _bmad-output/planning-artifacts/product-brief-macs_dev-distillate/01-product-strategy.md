## Product Strategy
- This section covers product strategy and intent. Part 1 of 4 from `product-brief-macs_dev.md` and `domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md`.

## Executive Summary
- MACS started as one controller supervising one worker via tmux + Python bridge; concept proven, but unsafe/insufficient for many heterogeneous agents in parallel.
- Product direction: open-source orchestration platform where one controller manages many worker windows across runtimes (Codex, Claude, Gemini, local agents) while retaining authority over routing, ownership, conflict boundaries, intervention, and recovery.
- Strategic position: mixed-runtime orchestration governance, not single-vendor framework competition; domain momentum favors durable state, interoperability, observability, human oversight, and replayable recovery.

## Problem
- Serious users can launch multiple sessions; they cannot safely coordinate them at production quality.
- Current MACS/ad hoc multi-agent workflows: responsibility ambiguity; informal routing; weak merge-conflict avoidance; context leakage; unclear ownership; silent coordination failure.
- Failure modes called out across sources: duplicate workers under same task identity; runtime appears healthy but unsafe to route; session fails/exhausts budget without reliable recovery; semantic conflicts slip through even when text merges cleanly; humans cannot tell who owns what.
- Cost of status quo: hidden damage, operator confusion, low trust in parallel execution.

## Solution
- Evolve MACS from supervision bridge into controller-owned orchestration plane.
- First production-grade release: one local orchestration controller; multiple tmux worker windows; pluggable runtime adapters; worker registry; capability metadata; controller-owned task state, leases, locks, routing, interventions, and recovery.
- Experience goal: assign and monitor parallel work across heterogeneous runtimes without losing control; make ownership explicit; route by policy + evidence; prevent unsafe parallel writes; surface token/session exhaustion when available; inspect, pause, reroute, and reconcile degraded workers.
- Domain research reinforces same approach: control-plane/execution-plane separation, evented state, evidence-backed adapters, catastrophe-drill testing, and workflow-level evaluation.

## Differentiation
- Controller-owned authority: control plane, not runtime, is authoritative for ownership, routing, and recovery.
- Heterogeneous runtime support: built to coordinate mixed vendors and local agents, not optimize for one runtime stack.
- Safe parallelisation: ownership, leases, locks, reconciliation gates, and semantic coordination are core requirements.
- Evidence-backed operation: adapter outputs classified by confidence/evidence instead of trusted blindly.
- Testable resilience: stale-state, split-brain, recovery, and coordination-failure scenarios belong in automated regression suites.
- Open-source production path: intended for maintainers and serious adopters in real repositories, not only internal demos.
- Research-backed whitespace: frameworks mostly focus on building agents; MACS can occupy neutral orchestration governance for mixed runtimes.

## Who This Serves
- Primary users: maintainers orchestrating their own work; need supervision of parallel heterogeneous workers with visibility, authority, recovery control.
- Secondary users: technical adopters wanting credible open-source foundation for serious multi-agent orchestration in their repositories.
- Tertiary users: contributors extending MACS and runtime adapters; need clean orchestration model, pluggable adapter boundaries, strong tests.
- "Aha" moment: many heterogeneous workers run in parallel under one controller while ownership, lock state, intervention options, and recovery remain legible.

## Success Criteria
- 6-12 month success: repeated real parallel workflows across mixed runtimes without coordination breakdown.
- Strong automated regression coverage for routing, locking, ownership, intervention, recovery behavior.
- Maintainers can use MACS in real repos with confidence that failures are visible and recoverable.
- Early adopters regard MACS as credible open-source foundation for heterogeneous agent orchestration.
- Adoption friction low enough that serious technical users can configure mixed-runtime orchestration without bespoke per-repo glue.
- New runtime/orchestration contributions land against stable control-plane model instead of ad hoc session logic.

## Scope
- In scope for first production-grade release: one controller managing many tmux workers; adapters for Codex, Claude, Gemini, and one local/runtime-neutral option; worker registry/capability metadata; controller-owned routing/ownership; explicit locks/coordination boundaries; operator monitoring/intervention; token/session-limit visibility where available; comprehensive automated orchestration tests.
- Explicitly out of scope for MVP: fully autonomous self-replanning without oversight; cross-machine/distributed orchestration beyond local host; deep enterprise IAM/compliance packaging; broad marketplace/ecosystem layers beyond initial adapter model.
- Research-informed deferred direction: richer protocol interoperability, confidence-weighted scheduling, semantic integrity checks, replay tooling, broader observability normalization, maybe later distributed execution after local control model is stable.

## Technical Approach
- Conservative-to-balanced path: durable control core first (worker registry, task/lease state, protected-surface locks, event log, intervention controls); runtime adapters next; confidence-weighted routing, recovery semantics, richer coordination checks later.
- Discipline: local-host controller, bounded adapters, explicit safety boundaries, strong regression coverage before broader autonomy.
- Domain alignment: durable state, explicit workflows, observability, replayable recovery, protocol-friendly interoperability across mixed runtimes.

## Vision
- 2-3 year vision: trusted open-source orchestration control plane for heterogeneous agent runtimes; standard way to coordinate, observe, intervene in, and recover multi-agent work across vendors and local agents.
- End-state proof is not "many agents run at once"; it is "heterogeneous agent work is legible, governable, and resilient enough for production repositories."
