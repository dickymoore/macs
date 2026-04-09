---
title: "Product Brief: macs_dev"
status: "complete"
created: "2026-04-09T18:17:14+0100"
updated: "2026-04-09T18:20:12+0100"
inputs:
  - "/home/codexuser/macs_dev/docs/architecture.md"
  - "/home/codexuser/macs_dev/_bmad-output/brainstorming/brainstorming-session-2026-04-09-17-52-26.md"
  - "/home/codexuser/macs_dev/_bmad-output/planning-artifacts/research/domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md"
---

# Product Brief: MACS Multi-Agent Orchestration

**Phase Status:** Accepted Phase 1 Product Brief

## Executive Summary

MACS began as a practical way for one controller agent to supervise one worker through tmux and a Python bridge. That model proves the coordination concept, but it breaks down once serious users try to run many heterogeneous agents in parallel. Current MACS and ad hoc multi-agent setups can launch more agents, but they still lack the thing that makes parallel agent work trustworthy: a real orchestration control plane.

This product extends MACS into an open-source orchestration platform for mixed agent runtimes. The next version of MACS will allow one orchestration controller to manage many worker windows across runtimes such as Codex, Claude, Gemini, and local agents, while preserving controller-owned authority over task routing, ownership, conflict boundaries, intervention, and recovery. The value is not simply "more agents." The value is safe orchestration across heterogeneous agents that can work in parallel without silent coordination failure.

The timing is right because the broader ecosystem is moving in the same direction: durable state, protocol interoperability, traceability, human oversight, and replayable recovery are becoming the serious end of the market. MACS can occupy a clear open-source position by focusing on mixed-runtime orchestration governance rather than trying to become another single-vendor agent framework.

## The Problem

Maintainers and early technical adopters already know how to start multiple agent sessions. The hard part is coordinating them safely. In current MACS, the architecture still assumes one controller and one worker. In ad hoc multi-agent workflows, responsibility becomes ambiguous, routing is mostly informal, merge-conflict avoidance is weak, context leaks between sessions, and failures often leave humans guessing which agent owns what.

That gap makes serious parallel work fragile. Two workers can drift under the same task identity. A runtime can look healthy while actually becoming unsafe to route work to. A session can fail or exhaust budget without the controller having a reliable recovery path. Even when text merges cleanly, semantic conflicts can slip through because no control plane is managing coupled work surfaces. The cost of the status quo is not just inconvenience. It is hidden damage, operator confusion, and low trust in multi-agent execution.

## The Solution

MACS should evolve from a supervision bridge into a controller-owned orchestration plane. The first production-grade version will let one orchestration controller manage multiple tmux worker windows, each backed by a pluggable runtime adapter. Workers will expose capability and health metadata through adapters, but the controller will remain the authority on task state, leases, locks, routing decisions, interventions, and recovery.

The experience goal is straightforward: maintainers can assign and monitor parallel work across heterogeneous runtimes without losing control. The system should make ownership explicit, route work according to policy and evidence, prevent unsafe parallel writes through locks and coordination boundaries, surface token or session exhaustion where possible, and let operators inspect, pause, reroute, or reconcile workers across windows when something goes wrong. Comprehensive automated tests will validate orchestration behavior, not only individual scripts.

## What Makes This Different

Most current agent tooling focuses on building agents, not governing them. MACS can differentiate by treating orchestration as an operational control problem rather than a prompt-management problem.

The key differences are:

- **Controller-owned authority**: the control plane, not the worker runtime, is authoritative for ownership, routing, and recovery.
- **Heterogeneous runtime support**: MACS is designed to coordinate mixed vendors and local agents rather than optimize for one runtime stack.
- **Safe parallelisation**: explicit ownership, leases, locks, and reconciliation gates are core product requirements, not future polish.
- **Evidence-backed operation**: adapter outputs are treated as facts, signals, or claims with confidence, not as unquestioned truth.
- **Testable resilience**: split-brain, stale-state, and coordination-failure scenarios are meant to be exercised in automated regression suites.
- **Open-source production path**: the product is intended to be usable by maintainers and serious adopters in real repositories, not only as an internal experiment or framework demo.

This positions MACS as an open-source orchestration control plane with governance built in, rather than a thin launcher for multiple terminals.

## Who This Serves

**Primary users:** maintainers running orchestrated work themselves. They need to supervise parallel agent execution across windows and runtimes without losing visibility, authority, or recovery control.

**Secondary users:** technical adopters using MACS in their own repositories. They want a credible open-source foundation for serious multi-agent orchestration, not a brittle demo stack.

**Tertiary users:** contributors extending MACS and runtime adapters. They need a clean orchestration model, pluggable adapter boundaries, and strong tests so the system can grow without becoming ungovernable.

The "aha" moment is when a user sees multiple heterogeneous workers running in parallel under one controller and realizes the system still has clear ownership, visible lock state, operator intervention, and auditable recovery when conditions degrade.

## Success Criteria

Within 6-12 months, this initiative succeeds if:

- MACS can repeatedly run real parallel multi-agent workflows across mixed runtimes without coordination breakdowns.
- The orchestration layer has strong automated regression coverage for routing, locking, ownership, intervention, and recovery behavior.
- Maintainers can use the system in real repositories with confidence that orchestration failures are visible and recoverable.
- Early adopters view MACS as a credible open-source foundation for heterogeneous agent orchestration.
- Adoption friction is low enough that serious technical users can configure mixed-runtime orchestration without bespoke per-repo glue.
- Contributor work on new runtimes and orchestration features can land against a stable control-plane model rather than ad hoc session logic.

## Scope

### In Scope for the First Production-Grade Release

- One orchestration controller managing multiple tmux worker windows
- Pluggable runtime adapters for at least Codex, Claude, Gemini, and one local/runtime-neutral adapter
- Worker registry and capability metadata
- Controller-owned task routing and ownership
- Explicit locks and coordination boundaries for merge-conflict avoidance
- Operator monitoring and intervention across windows
- Token/session-limit visibility where available
- Comprehensive automated tests around orchestration, locking, routing, and recovery

### Explicitly Out of Scope for MVP

- Fully autonomous self-replanning without operator oversight
- Cross-machine or distributed orchestration beyond the local host
- Deep enterprise IAM/compliance packaging
- Broad marketplace or ecosystem layers beyond the initial adapter model

## Technical Approach

The product direction should follow a conservative-to-balanced architecture path. Start with a durable control core: worker registry, task/lease state, protected-surface locks, event log, and intervention controls. Layer in runtime adapters that provide evidence-bearing capability and health data. Add confidence-weighted routing, recovery semantics, and richer coordination checks once the controller-owned authority model is stable.

This keeps the MVP disciplined: one local-host orchestration controller, bounded runtime adapters, explicit safety boundaries, and strong regression coverage before broader autonomy or distributed execution. It also keeps MACS aligned with where the domain is heading: durable state, explicit workflows, observability, replayable recovery, and protocol-friendly interoperability across mixed runtimes.

## Vision

If this succeeds, MACS becomes the trusted open-source orchestration control plane for heterogeneous agent runtimes. It becomes the standard way to coordinate, observe, intervene in, and safely recover multi-agent work across vendors and local agents, with governance and evidence built into the core.

In 2-3 years, MACS should not merely prove that many agents can run at once. It should prove that heterogeneous agent work can be made legible, governable, and resilient enough for production-grade use in real software repositories.
