# Epic 1 Retrospective

Date: 2026-04-14
Epic: 1
Epic Title: Govern Approved Surface Versions and Secret Access
Lane: Governance Hardening
Status: complete

## Epic Review

Epic 1 finished with all four governance-hardening stories complete and accepted:

- `1.1` added controller-owned `surface_version_pins`, operating-profile-aware resolution, and snapshot-aware inspection summaries.
- `1.2` enforced fail-closed version-pin checks during worker registration and routing, including quarantine evidence for drifted workers.
- `1.3` added controller-owned `secret_scopes`, inspectable summaries, and rejection or scrubbing of inline secret-material fields.
- `1.4` enforced action-time scoped-secret resolution before assignment or dispatch while keeping raw secret values out of controller state and audit output.

The sequence held up. Policy modeling and inspection landed before fail-closed enforcement, and secret handling followed the same progression. That kept controller-owned semantics stable before high-risk blocking behavior was introduced.

## What Worked

- Reusing the existing controller seams in `policy.py`, `setup.py`, `cli/main.py`, `routing.py`, and `tasks.py` kept authority centralized instead of creating parallel governance subsystems.
- The lane stayed disciplined about explicit absence and backward compatibility. `none_configured` states, scoped applicability summaries, and no-regression paths kept governance hardening from silently changing older repos.
- Review follow-ups materially improved the outcome. Snapshot staleness visibility, declared-surface filtering, live runtime-probe requirements, quarantine audit events, and inline-secret scrubbing all closed real governance gaps before closeout.
- Focused story regressions plus full orchestration discovery on each increment made it practical to harden shared controller seams without losing confidence in the broader orchestration surface.

## Friction and Risks

- Human-readable read-side output still lagged behind JSON or state-layer changes often enough that explicit read-side acceptance remains necessary on every governance story.
- The hardest bugs in this lane were permissive fallbacks. Story `1.2` needed follow-up tightening so runtime-only pins relied on live probe evidence, and Story `1.4` initially regressed non-secret-backed flows until the gate was narrowed to policy-applicable surfaces.
- Secret-scope modeling was not enough by itself; Story `1.3` still required a high-severity follow-up to reject and scrub inline secret-like fields so inspection paths could not preserve unsafe policy input.
- Epic 2 will extend these controls into diff/review checkpoints and release evidence. Freshness, stale-context detection, and remediation guidance are still the main correctness risks as the lane moves from policy hardening into closeout gating.

## Follow-Through From Previous Retrospectives

This is the first retrospective artifact for the governance-hardening lane. The historical orchestration Epic 1 retrospective remains a separate initiative and did not create carry-forward items for this lane-local backlog.

## Next Epic Preparation

Epic 2 should extend the same controller-owned, fail-closed discipline into attributable review gating:

- Story `2.1` should define one controller-owned diff or review checkpoint artifact linked to task, actor, repo state, affected refs, and canonical decision events.
- Story `2.2` should enforce checkpoint freshness before close/archive or safety-relaxing actions, reusing the existing task, routing, and event seams instead of inventing a second approval path.
- Story `2.3` should surface version-pin, secret-scope, and checkpoint evidence together in inspect and release-review outputs without adding a parallel evidence store.

## Action Items

- Controller and policy seams: keep fail-closed defaults and explicit remediation text as diff or review checkpoint enforcement is added in Epic 2.
- CLI and inspect surfaces: treat human-readable parity with JSON evidence as acceptance criteria, not follow-up polish.
- Test ownership for governance hardening: keep targeted red or green regressions plus full orchestration discovery for stale evidence, repo-state mismatch, and redaction boundaries.
