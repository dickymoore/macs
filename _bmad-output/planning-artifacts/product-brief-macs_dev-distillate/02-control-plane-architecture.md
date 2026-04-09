## Control-Plane Architecture
- This section covers architecture, control semantics, and implementation sequence. Part 2 of 4 from `product-brief-macs_dev.md` and `domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md`.

## Control Model
- Required core schema: worker, task, lease, lock, event, override, reconciliation; research also calls for capability metadata, health evidence, and protected-surface semantics.
- Controller-owned truth is mandatory; external runtimes/adapters are execution surfaces that report evidence-bearing state, not the system of record.
- Distinguish evidence classes explicitly: authoritative fact; soft signal; untrusted claim.
- Protected-surface locks are needed for merge-conflict avoidance; semantic coordination must extend beyond line-level conflicts.
- Ownership model needs split-brain prevention, lease lifecycle, stale-state detection, explicit intervention paths, and visible lock state.

## Runtime Adapters
- Initial adapter target set: Codex, Claude, Gemini, one local/runtime-neutral adapter.
- Adapters should expose capability + health metadata; trust level should vary by signal quality, freshness, corroboration, and interruptibility.
- Adapter contracts should support capability freshness, token/session-limit visibility where available, pause/resume/intervention hooks, and failure evidence suitable for routing decisions.
- Architecture should remain independent of any single vendor worldview even when integrating MCP, A2A, OpenAI Agents SDK, Anthropic Claude Code SDK, Google ADK, Microsoft Agent Framework, LangGraph/LangSmith, or CrewAI-style patterns.

## Durable Execution Patterns
- Domain direction favors durable, stateful execution over stateless request/response.
- Relevant patterns found across ecosystem: graph workflows, session state, middleware, telemetry, checkpointing, persistence, streaming, human-in-the-loop checkpoints, rewind, retries, replay, scheduling, concurrent input handling.
- MACS should adopt durable/evented control semantics without assuming runtime-side rewind is atomic or sufficient.
- ADK rewind warning matters: session state, artifacts, and event persistence are not one atomic transaction; external side effects are not automatically restored.
- Recovery design must therefore assume controller truth + explicit compensation/reconciliation, not magical rollback.

## Routing, Scheduling, and Intervention
- Near-term routing strategy: controller routes by policy + evidence; confidence-weighted scheduling comes after control core stabilizes.
- Critical routing checks: health corroboration, capability freshness, interruptibility, current lease/lock state, operator policy, and failure history.
- Native operator features required: checkpoints, pause/resume, reroute, override, reconciliation workflows, degradation visibility.
- Token/quota/session exhaustion should be surfaced where adapters can detect it; lack of visibility is itself routing-relevant evidence.

## Observability and Eventing
- Instrument around events, traces, replayable state transitions, and event history rather than ad hoc terminal introspection.
- OpenTelemetry generative-AI semantic conventions and Azure AI Foundry multi-agent observability work indicate trace normalization is becoming infrastructure.
- Observability is necessary but insufficient; traces cannot be treated as proof of correctness without additional coordination and policy checks.
- Event log should support audit, replay, incident analysis, test assertions, and operator understanding of who did what, when, and under which approvals/overrides.

## Failure Model
- First-order technical risks: state divergence; semantic collision; stale-but-plausible telemetry; partial/false confidence from traces; over-complex orchestration policy.
- Product brief failure cases + research failure cases align: duplicate task ownership; unsafe but apparently healthy runtime; budget/session exhaustion; semantic conflicts despite clean text merges; non-atomic recovery across side effects.
- Design principle: failure containment before autonomy; strong split-brain containment, reconciliation gates, and explicit unsafe-to-route states.

## Implementation Framework
- Phase 1: durable control architecture: worker/task registry, lease lifecycle, coarse protected-surface locks, event log, intervention model.
- Phase 2: evidence-backed adapters + confidence-weighted dispatch/scheduling.
- Phase 3: semantic integrity checks, reconciliation gates, replay-driven failure testing, richer protocol interoperability, trace normalization.
- Innovation roadmap from research: registry/leaves/locks/event log -> adapter evidence contracts/confidence routing -> semantic coordination/failure drills -> broader interoperability -> workflow-level evaluation + replay in CI/CD.
- Keep local-host orchestration as first boundary; defer distributed/cross-machine operation until authority and failure semantics are proven.

## Implementation Opportunities
- Mixed-runtime orchestration viability improves as protocols and trace semantics normalize.
- Evented session models create room for controller-owned truth and replayable failure handling.
- Human-in-the-loop checkpoints are mainstream runtime features now; MACS can build them into orchestration instead of bolting them on.
- Workflow-level evaluation and trace grading make behavior-level regression testing feasible, not just unit testing scripts.

## Architecture Decisions and Rejected Paths
- Decision: build controller-owned control plane. Reason: safe coordination requires central truth for ownership, routing, locks, interventions, recovery.
- Rejected: rely on runtime-native authority or optimism. Reason: heterogeneous runtimes produce partial, stale, or misleading signals; trust must be calibrated.
- Rejected for MVP: distributed orchestration, deep enterprise packaging, full self-replanning autonomy. Reason: local durable control and safety boundaries must harden first.
