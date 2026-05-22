# MACS Multi-Agent Orchestration Diagram Pack

**Date:** 2026-04-09  
**Purpose:** Mermaid architecture/orchestration diagram pack for the MACS multi-agent orchestration proposal  
**Grounded In:**  
- `/home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev.md`
- `/home/codexuser/macs_dev/_bmad-output/planning-artifacts/research/domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md`

## Scope

This pack visualizes the proposed MACS control plane with emphasis on:

- controller-owned authority
- worker registry and capability evidence
- pluggable runtime adapters
- locks, ownership, and coordination boundaries
- operator intervention paths
- token/session monitoring
- recovery and reconciliation loops

## Diagram 1: Control Plane Overview

```mermaid
flowchart TB
    operator["Operator / Maintainer"]

    subgraph cp["MACS Controller-Owned Control Plane"]
        controller["Orchestration Controller"]
        router["Policy + Evidence Router"]
        registry["Worker Registry"]
        taskstore["Task / Lease Store"]
        lockstore["Lock / Ownership Store"]
        eventlog["Event Log / Audit Trail"]
        recovery["Recovery + Reconciliation Engine"]
        monitor["Session / Token Monitor"]
        intervention["Intervention Controls"]
    end

    subgraph runtime["Runtime Adapter Layer"]
        codex["Codex Adapter"]
        claude["Claude Adapter"]
        gemini["Gemini Adapter"]
        local["Local / Neutral Adapter"]
    end

    subgraph workers["tmux Worker Windows"]
        w1["Worker A"]
        w2["Worker B"]
        w3["Worker C"]
        w4["Worker D"]
    end

    operator --> controller
    operator --> intervention
    controller --> router
    controller --> registry
    controller --> taskstore
    controller --> lockstore
    controller --> eventlog
    controller --> monitor
    controller --> recovery
    controller --> intervention

    router --> codex
    router --> claude
    router --> gemini
    router --> local

    registry <-->|capabilities, health, freshness| codex
    registry <-->|capabilities, health, freshness| claude
    registry <-->|capabilities, health, freshness| gemini
    registry <-->|capabilities, health, freshness| local

    monitor <-->|quota, session, liveness| codex
    monitor <-->|quota, session, liveness| claude
    monitor <-->|quota, session, liveness| gemini
    monitor <-->|quota, session, liveness| local

    intervention --> codex
    intervention --> claude
    intervention --> gemini
    intervention --> local

    codex --> w1
    claude --> w2
    gemini --> w3
    local --> w4

    w1 --> eventlog
    w2 --> eventlog
    w3 --> eventlog
    w4 --> eventlog
```

**Interpretation:** The controller remains authoritative for routing, lease state, locks, interventions, and recovery. Adapters expose evidence and control hooks, but they do not become the source of truth.

## Diagram 2: Task Dispatch and Evidence-Backed Routing

```mermaid
sequenceDiagram
    actor Operator
    participant Controller as Orchestration Controller
    participant Locks as Lock/Ownership Store
    participant Registry as Worker Registry
    participant Router as Policy + Evidence Router
    participant Adapter as Runtime Adapter
    participant Worker as tmux Worker
    participant Events as Event Log

    Operator->>Controller: Submit task with scope and intent
    Controller->>Locks: Check protected surfaces and ownership conflicts
    Locks-->>Controller: Lock status and allowed boundaries
    Controller->>Registry: Query eligible workers
    Registry-->>Controller: Capabilities, health, freshness, session state
    Controller->>Router: Evaluate policy + evidence
    Router-->>Controller: Ranked worker choice with confidence
    Controller->>Locks: Create lease and reserve work surface
    Controller->>Adapter: Dispatch task with lease ID and limits
    Adapter->>Worker: Deliver task into runtime session
    Worker-->>Adapter: Ack or reject
    Adapter-->>Controller: Delivery result + evidence
    Controller->>Events: Persist assignment, lease, and routing evidence
    Controller-->>Operator: Visible assignment and current owner
```

**Interpretation:** Routing is not a blind "send to any idle worker" step. It is gated by lock state, worker evidence, and explicit lease creation before the task enters a runtime session.

## Diagram 3: Ownership, Locks, and Safe Parallelisation

```mermaid
stateDiagram-v2
    [*] --> Unassigned
    Unassigned --> Candidate: task proposed
    Candidate --> Reserved: worker selected
    Reserved --> Active: lease accepted
    Reserved --> Unassigned: dispatch rejected

    state Active {
        [*] --> Owned
        Owned --> Blocked: conflicting surface requested
        Blocked --> Owned: conflict cleared
        Owned --> InterventionHold: operator pause or override
        InterventionHold --> Owned: operator resume
        Owned --> Expiring: heartbeat stale or budget low
        Expiring --> Reconcile: lease expired or session degraded
        Owned --> Reconcile: semantic conflict detected
        Reconcile --> Owned: ownership reaffirmed
        Reconcile --> Split: competing ownership detected
        Split --> InterventionHold: force review
    }

    Active --> Completed: task finished and lock released
    Active --> Failed: unrecoverable error
    Failed --> Reconcile: recovery attempt
    Reconcile --> Reserved: reroute with new lease
    Completed --> [*]
```

**Interpretation:** Safe parallelisation depends on explicit state transitions, not informal etiquette between workers. The critical failure to contain is split-brain ownership over the same protected surface.

## Diagram 4: Intervention and Operator Control Paths

```mermaid
flowchart LR
    alert["Alert or Operator Concern"] --> classify{"What kind of issue?"}

    classify -->|Unsafe write conflict| pause["Pause affected leases"]
    classify -->|Stale session / quota risk| reroute["Prepare reroute"]
    classify -->|Bad output / drift| inspect["Open worker context and inspect"]
    classify -->|Adapter misreporting| quarantine["Quarantine worker"]

    pause --> review["Operator review"]
    inspect --> review
    quarantine --> review
    reroute --> review

    review --> action{"Operator action"}
    action -->|Resume| resume["Resume current lease"]
    action -->|Reassign| assign["Assign new worker and lease"]
    action -->|Reconcile| reconcile["Create reconciliation task"]
    action -->|Abort| abort["Terminate lease and release lock"]

    resume --> audit["Record override and rationale"]
    assign --> audit
    reconcile --> audit
    abort --> audit
```

**Interpretation:** Intervention is a first-class orchestration feature. The operator is not outside the system; the operator acts through explicit pause, resume, reroute, reconcile, and abort controls that are logged.

## Diagram 5: Session and Token Monitoring Loop

```mermaid
flowchart TB
    subgraph signals["Observed Signals"]
        heartbeat["Heartbeat / Liveness"]
        tokens["Token Budget / Quota"]
        session["Session Age / State Freshness"]
        adapter["Adapter Health"]
        output["Output Progress / Events"]
    end

    subgraph monitor["Monitoring Logic"]
        collect["Collect signals"]
        score["Compute risk score"]
        classify["Classify: healthy / degraded / unsafe"]
    end

    subgraph actions["Controller Actions"]
        continue["Continue routing"]
        throttle["Throttle new assignments"]
        warn["Raise operator warning"]
        checkpoint["Checkpoint or compact context"]
        drain["Drain worker from new work"]
        recover["Trigger recovery workflow"]
    end

    heartbeat --> collect
    tokens --> collect
    session --> collect
    adapter --> collect
    output --> collect
    collect --> score
    score --> classify

    classify -->|healthy| continue
    classify -->|degraded| throttle
    classify -->|degraded| warn
    classify -->|degraded| checkpoint
    classify -->|unsafe| drain
    classify -->|unsafe| recover
```

**Interpretation:** Monitoring is operational, not cosmetic. Token exhaustion, stale sessions, and weak adapter health become scheduling and recovery inputs before they become silent failures.

## Diagram 6: Recovery and Reconciliation Loop

```mermaid
sequenceDiagram
    participant Monitor as Session/Token Monitor
    participant Controller as Orchestration Controller
    participant Events as Event Log
    participant Recovery as Recovery Engine
    participant Registry as Worker Registry
    participant AdapterA as Current Adapter
    participant AdapterB as Alternate Adapter
    actor Operator

    Monitor->>Controller: Degraded or unsafe worker signal
    Controller->>Events: Persist anomaly and freeze risky routing
    Controller->>Recovery: Start recovery workflow
    Recovery->>AdapterA: Attempt checkpoint, pause, or graceful interrupt
    AdapterA-->>Recovery: Partial state, failure, or no response
    Recovery->>Events: Record recovery evidence
    Recovery->>Registry: Request alternate worker candidates
    Registry-->>Recovery: Candidates with capability and freshness evidence
    Recovery->>Operator: Present recovery options if confidence is low
    Operator-->>Recovery: Approve retry, reroute, or abort
    Recovery->>AdapterB: Re-dispatch from controller-owned state
    AdapterB-->>Controller: New lease acknowledged
    Controller->>Events: Persist reconciliation and ownership transfer
```

**Interpretation:** Recovery uses controller-owned state and evidence from the event log, not optimistic assumptions that the failing runtime can fully restore itself. Human approval remains available when confidence is weak.

## Design Notes

- The control plane owns truth for `worker`, `task`, `lease`, `lock`, `event`, `override`, and `reconciliation` state.
- Runtime adapters are intentionally bounded. They expose facts, signals, and claims with freshness and confidence, but policy semantics stay in MACS.
- Locks should begin coarse, around protected surfaces such as file sets, branches, or task scopes, before moving to finer semantic coordination.
- Intervention paths should be auditable by default so pause, reroute, and abort decisions are replayable in failure reviews.
- Recovery should assume external side effects are not atomically reversible. Reconciliation is therefore mandatory after degraded sessions or competing ownership claims.

## Mapping Back to Source Artifacts

- The brief establishes controller-owned authority over routing, ownership, leases, locks, intervention, and recovery.
- The brief also defines worker registry, pluggable adapters, operator monitoring, token/session visibility, and automated orchestration tests as first-release scope.
- The research report reinforces control-plane versus execution-plane separation, evidence-backed adapter contracts, durable state, operator checkpoints, telemetry normalization, and replayable recovery.
- The research report also identifies split-brain ownership, stale evidence, quota/session degradation, and non-atomic recovery as core risks the architecture must visibly contain.
