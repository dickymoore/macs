---
project_name: 'macs_dev'
user_name: 'Dicky'
date: '2026-04-09T19:00:00+01:00'
sections_completed:
  - 'technology_stack'
  - 'language_rules'
  - 'framework_rules'
  - 'testing_rules'
  - 'quality_rules'
  - 'workflow_rules'
  - 'anti_patterns'
status: 'complete'
rule_count: 24
optimized_for_llm: true
existing_patterns_found: 11
source_documents:
  - '/home/codexuser/macs_dev/_bmad-output/planning-artifacts/product-brief-macs_dev.md'
  - '/home/codexuser/macs_dev/_bmad-output/planning-artifacts/research/domain-multi-agent-orchestration-and-agent-runtime-orchestration-for-macs-research-2026-04-09.md'
  - '/home/codexuser/macs_dev/_bmad-output/brainstorming/brainstorming-session-2026-04-09-17-52-26.md'
project_type: 'brownfield open-source orchestration project'
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- Bash shell scripts are the primary operational surface; use `#!/usr/bin/env bash` and `set -euo pipefail`.
- Python bridge code targets Python 3.8+ and currently uses the standard library only; do not introduce third-party Python dependencies without explicit justification.
- tmux is a hard runtime dependency for orchestration behavior, pane discovery, busy detection, and smoke testing.
- Codex CLI is the default controller/worker runtime; Claude Code is also supported operationally.
- Repo-local runtime state lives under `.codex/` in the target repo; MACS writes wrapper scripts and tmux metadata there.
- Documentation is Markdown-first under `README.md` and `docs/`.
- Automated validation currently centers on ShellCheck for shell scripts and `tools/tmux_bridge/tests/smoke.sh` for integration behavior.
- Phase 1 product direction extends the current tmux bridge into a local-host, multi-worker, mixed-runtime orchestration control plane.

## Critical Implementation Rules

### Language-Specific Rules

- Preserve the current split: thin root launchers at repo root, operational logic under `tools/tmux_bridge/`.
- In shell scripts, quote expansions consistently, prefer local variables inside functions, and keep stateful paths explicit.
- In Python, prefer small stdlib functions over framework introduction; maintain readable procedural control flow unless a clear abstraction boundary exists.
- When invoking subprocesses from Python, keep arguments as lists, not shell strings, unless shell behavior is required and justified.
- Treat filesystem writes as part of the orchestration contract: use explicit paths, UTF-8 text, and deterministic filenames.

### Framework-Specific Rules

- The controller remains authoritative; worker runtimes and adapters can report status, but they must not become the source of truth for ownership or routing.
- Design new orchestration features around canonical entities discussed in Phase 1 artifacts: `worker`, `task`, `lease`, `lock`, and `event`.
- Prefer local-host orchestration semantics first. Do not quietly introduce distributed, multi-machine, or enterprise control-plane assumptions.
- Keep adapter boundaries skeptical: model runtime outputs as facts, soft signals, or untrusted claims rather than raw truth.
- Preserve repo-local state conventions and backward compatibility where already present, including legacy fallback behavior such as `tools/tmux_bridge/target_pane.txt`.

### Testing Rules

- Any change affecting routing, targeting, session discovery, or send/snapshot/status behavior should be covered by the smoke test or an adjacent integration-style shell test.
- Tests must avoid contaminating the user’s live tmux environment; follow the existing pattern of temporary sockets, temporary sessions, and cleanup traps.
- Add regression coverage for failure containment, not just happy paths. Phase 1 priorities include stale state, split-brain ownership, session divergence, and cross-session contamination.
- When adding controller-state features, make state transitions explicit and testable rather than implicit in control flow.

### Code Quality & Style Rules

- Keep scripts focused and atomic. MACS favors narrow helpers such as `snapshot.sh`, `send.sh`, `status.sh`, and `set_target.sh` over large multipurpose entrypoints.
- Maintain documentation parity with behavior changes. User-facing operational changes usually require updates in `README.md`, `docs/`, or both.
- Preserve open-source usability: defaults should work from a cloned repo with minimal setup and should not assume internal infrastructure.
- Prefer explicit, auditable behavior over clever automation. Hidden coupling is a bug in orchestration code.

### Development Workflow Rules

- Treat this repo as brownfield: extend existing behavior instead of rewriting surfaces that already encode compatibility assumptions.
- Keep changes focused and atomic, consistent with `CONTRIBUTING.md`.
- Do not edit planning artifacts as part of implementation work unless the task explicitly asks for planning metadata or new planning outputs.
- When generating repo-local helper state, write under `.codex/` rather than introducing new scattered hidden directories.

### Critical Don't-Miss Rules

- Do not collapse controller and worker responsibilities. MACS’s core value is governance separation between decision-making and execution.
- Do not trust apparent runtime health without freshness and corroboration; stale-but-plausible state is a known Phase 1 design risk.
- Do not optimize for raw parallelism before ownership, lease, and lock semantics are explicit.
- Do not assume clean text merges imply safe orchestration. Behaviorally coupled surfaces may still need coordination.
- Do not add hidden global state that bypasses repo-local targeting files, tmux metadata, or explicit session selection.
- Do not introduce adapter features that make recovery or operator intervention harder to inspect, pause, replay, or override.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing orchestration, tmux bridge, adapter, or repo bootstrap changes.
- Prefer the more conservative control-plane interpretation when requirements are ambiguous.
- Align new work with the accepted Phase 1 direction: controller-owned authority, evidence-backed routing, explicit coordination boundaries, and replayable recovery.
- Update this file when the stack, orchestration model, or enforcement rules materially change.

**For Humans:**

- Keep this file lean and specific to agent implementation behavior.
- Update it when brownfield conventions change or Phase 1 architecture decisions become concrete code-level rules.
- Remove rules that become obsolete, duplicated, or too obvious to justify context space.

Last Updated: 2026-04-09
