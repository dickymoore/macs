#!/usr/bin/env python3
"""Repo-local routing and governance policy bootstrap plus policy helpers."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.store import connect_state_db


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


DEFAULT_ROUTING_POLICY = {
    "policy_version": "phase1-defaults-v1",
    "workflow_defaults": {
        "documentation_context": {
            "preferred_runtimes": ["codex", "claude"],
            "disallowed_states": ["degraded", "unavailable", "quarantined"],
        },
        "planning_docs": {"preferred_runtimes": ["claude", "codex", "gemini"]},
        "solutioning": {"preferred_runtimes": ["claude", "codex", "gemini"]},
        "implementation": {
            "preferred_runtimes": ["codex", "claude", "local"],
            "require_interruptibility": True,
        },
        "review": {"preferred_runtimes": ["codex", "claude", "gemini"]},
        "privacy_sensitive_offline": {
            "preferred_runtimes": ["local"],
            "forbid_networked_tools": True,
        },
    },
}
DEFAULT_POLICY = DEFAULT_ROUTING_POLICY

DEFAULT_GOVERNANCE_POLICY = {
    "policy_version": "phase1-governance-v1",
    "governed_surfaces": {
        "allowlisted_surfaces": [],
        "pinned_surfaces": {},
    },
    "workflow_surface_overrides": {
        "privacy_sensitive_offline": {
            "allowlisted_surfaces": [],
            "pinned_surfaces": {},
        }
    },
    "audit_content": {
        "prompt_content": {"mode": "omit"},
        "terminal_snapshot": {"mode": "omit"},
        "tool_output": {"mode": "omit"},
    },
}

GOVERNED_SURFACE_TAG_PREFIX = "surface:"
AUDIT_CONTENT_RETENTION_MODES = {"retain", "redact", "omit"}


@dataclass(frozen=True)
class DecisionRightsSpec:
    action_key: str
    decision_class: str
    confirmation_required: bool
    supported: bool
    policy_message: str


DECISION_RIGHTS_SPECS = {
    "task.assign": DecisionRightsSpec(
        action_key="task.assign",
        decision_class="policy_automatic",
        confirmation_required=False,
        supported=True,
        policy_message="controller executed assignment within policy-automatic bounds",
    ),
    "task.pause": DecisionRightsSpec(
        action_key="task.pause",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=True,
        policy_message="explicit operator confirmation accepted",
    ),
    "task.resume": DecisionRightsSpec(
        action_key="task.resume",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=True,
        policy_message="explicit operator confirmation accepted",
    ),
    "task.reroute": DecisionRightsSpec(
        action_key="task.reroute",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=True,
        policy_message="explicit operator confirmation accepted",
    ),
    "task.abort": DecisionRightsSpec(
        action_key="task.abort",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=False,
        policy_message="is not implemented in Phase 1",
    ),
    "recovery.retry": DecisionRightsSpec(
        action_key="recovery.retry",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=True,
        policy_message="explicit operator confirmation accepted",
    ),
    "recovery.reconcile": DecisionRightsSpec(
        action_key="recovery.reconcile",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=True,
        policy_message="explicit operator confirmation accepted",
    ),
    "worker.disable": DecisionRightsSpec(
        action_key="worker.disable",
        decision_class="policy_automatic",
        confirmation_required=False,
        supported=True,
        policy_message="controller executed worker drain within policy-automatic bounds",
    ),
    "worker.quarantine": DecisionRightsSpec(
        action_key="worker.quarantine",
        decision_class="policy_automatic",
        confirmation_required=False,
        supported=True,
        policy_message="controller executed worker quarantine within policy-automatic bounds",
    ),
    "lock.override": DecisionRightsSpec(
        action_key="lock.override",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=False,
        policy_message="is not implemented in Phase 1",
    ),
    "lock.release": DecisionRightsSpec(
        action_key="lock.release",
        decision_class="operator_confirmed",
        confirmation_required=True,
        supported=False,
        policy_message="is not implemented in Phase 1",
    ),
    # Forbidden MVP examples remain defined centrally even before the CLI grows verbs for them.
    "governance.auto_push": DecisionRightsSpec(
        action_key="governance.auto_push",
        decision_class="forbidden_in_mvp",
        confirmation_required=False,
        supported=False,
        policy_message="is forbidden in Phase 1",
    ),
    "governance.remote_operation": DecisionRightsSpec(
        action_key="governance.remote_operation",
        decision_class="forbidden_in_mvp",
        confirmation_required=False,
        supported=False,
        policy_message="is forbidden in Phase 1",
    ),
}


@dataclass(frozen=True)
class PolicyBootstrapResult:
    policy_path_created: bool
    snapshot_created: bool
    policy_path: Path
    snapshot_id: str
    governance_policy_path_created: bool
    governance_snapshot_created: bool
    governance_policy_path: Path
    governance_snapshot_id: str


@dataclass(frozen=True)
class _SinglePolicyBootstrapResult:
    policy_path_created: bool
    snapshot_created: bool
    policy_path: Path
    snapshot_id: str


def decision_rights_spec(action_key: str) -> DecisionRightsSpec:
    try:
        return DECISION_RIGHTS_SPECS[action_key]
    except KeyError as exc:
        raise KeyError(f"Unknown decision-rights action: {action_key}") from exc


def evaluate_decision_rights(
    action_key: str,
    *,
    confirmed: bool = False,
) -> dict[str, object]:
    spec = decision_rights_spec(action_key)
    allowed = True
    error_code: str | None = None
    error_exit_code: int | None = None
    policy_message = spec.policy_message
    if not spec.supported:
        allowed = False
        policy_message = f"Action '{action_key}' {spec.policy_message}; controller state remains unchanged"
        error_code = "policy_blocked" if spec.decision_class == "forbidden_in_mvp" else "unsupported"
        error_exit_code = 4 if spec.decision_class == "forbidden_in_mvp" else 5
    elif spec.confirmation_required and not confirmed:
        allowed = False
        policy_message = (
            f"Action '{action_key}' requires explicit operator confirmation via --confirm; "
            "controller state remains unchanged"
        )
        error_code = "policy_blocked"
        error_exit_code = 4
    return {
        "action_key": spec.action_key,
        "decision_class": spec.decision_class,
        "confirmation_required": spec.confirmation_required,
        "operator_confirmation_received": bool(spec.confirmation_required and confirmed),
        "allowed": allowed,
        "policy_message": policy_message,
        "error_code": error_code,
        "error_exit_code": error_exit_code,
    }


def routing_policy_path(orchestration_dir: Path) -> Path:
    return orchestration_dir / "routing-policy.json"


def governance_policy_path(orchestration_dir: Path) -> Path:
    return orchestration_dir / "governance-policy.json"


def bootstrap_policies(orchestration_dir: Path, state_db: Path) -> PolicyBootstrapResult:
    routing = _bootstrap_policy(
        policy_path=routing_policy_path(orchestration_dir),
        default_policy=DEFAULT_ROUTING_POLICY,
        state_db=state_db,
        snapshot_metadata_key="active_policy_snapshot_id",
    )
    governance = _bootstrap_policy(
        policy_path=governance_policy_path(orchestration_dir),
        default_policy=DEFAULT_GOVERNANCE_POLICY,
        state_db=state_db,
        snapshot_metadata_key="active_governance_policy_snapshot_id",
    )
    return PolicyBootstrapResult(
        policy_path_created=routing.policy_path_created,
        snapshot_created=routing.snapshot_created,
        policy_path=routing.policy_path,
        snapshot_id=routing.snapshot_id,
        governance_policy_path_created=governance.policy_path_created,
        governance_snapshot_created=governance.snapshot_created,
        governance_policy_path=governance.policy_path,
        governance_snapshot_id=governance.snapshot_id,
    )


def _bootstrap_policy(
    *,
    policy_path: Path,
    default_policy: dict[str, object],
    state_db: Path,
    snapshot_metadata_key: str,
) -> _SinglePolicyBootstrapResult:
    policy_created = not policy_path.exists()
    if policy_created:
        policy_path.write_text(json.dumps(default_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    policy = _load_policy(policy_path)
    conn = connect_state_db(state_db)
    try:
        existing = conn.execute(
            "SELECT snapshot_id FROM policy_snapshots WHERE policy_version = ? AND policy_origin = ?",
            (policy["policy_version"], str(policy_path)),
        ).fetchone()
        if existing is None:
            snapshot_id = f"policy-{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO policy_snapshots(snapshot_id, policy_origin, policy_version, captured_at, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    str(policy_path),
                    policy["policy_version"],
                    utc_now(),
                    json.dumps(policy, sort_keys=True),
                ),
            )
            conn.execute(
                """
                INSERT INTO metadata(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (snapshot_metadata_key, snapshot_id),
            )
            conn.commit()
            snapshot_created = True
        else:
            snapshot_id = existing["snapshot_id"]
            snapshot_created = False
    finally:
        conn.close()

    return _SinglePolicyBootstrapResult(
        policy_path_created=policy_created,
        snapshot_created=snapshot_created,
        policy_path=policy_path,
        snapshot_id=snapshot_id,
    )


def load_routing_policy(policy_path: Path) -> dict[str, object]:
    return _load_policy(policy_path)


def load_governance_policy(policy_path: Path) -> dict[str, object]:
    return _load_policy(policy_path)


def _load_policy(policy_path: Path) -> dict[str, object]:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def effective_surface_policy(
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
) -> dict[str, object]:
    base = governance_policy.get("governed_surfaces", {})
    allowlisted = set(_load_string_list(base.get("allowlisted_surfaces")))
    pinned_surfaces = _load_surface_pin_map(base.get("pinned_surfaces"))

    overrides = governance_policy.get("workflow_surface_overrides", {})
    workflow_override = overrides.get(workflow_class or "", {})
    allowlisted.update(_load_string_list(workflow_override.get("allowlisted_surfaces")))
    override_pins = _load_surface_pin_map(workflow_override.get("pinned_surfaces"))
    for surface_id, adapters in override_pins.items():
        pinned_surfaces[surface_id] = adapters

    return {
        "allowlisted_surfaces": sorted(allowlisted),
        "pinned_surfaces": pinned_surfaces,
    }


def describe_adapter_governance(
    adapter_descriptor: dict[str, object],
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
) -> dict[str, object]:
    effective_policy = effective_surface_policy(governance_policy, workflow_class=workflow_class)
    declared_surfaces = []
    allowlisted = set(effective_policy["allowlisted_surfaces"])
    pinned_surfaces = effective_policy["pinned_surfaces"]
    for surface_id in _load_string_list(adapter_descriptor.get("governed_surfaces")):
        declared_surfaces.append(
            {
                "surface_id": surface_id,
                "allowlisted": surface_id in allowlisted,
                "pinned_adapters": pinned_surfaces.get(surface_id, []),
            }
        )
    return {
        "policy_version": governance_policy.get("policy_version"),
        "workflow_class": workflow_class,
        "declared_surfaces": declared_surfaces,
    }


def evaluate_worker_governance(
    worker: dict[str, object],
    adapter_descriptor: dict[str, object],
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
) -> dict[str, object]:
    effective_policy = effective_surface_policy(governance_policy, workflow_class=workflow_class)
    declared_surfaces = set(_load_string_list(adapter_descriptor.get("governed_surfaces")))
    allowlisted = set(effective_policy["allowlisted_surfaces"])
    pinned_surfaces = effective_policy["pinned_surfaces"]
    active_surfaces = sorted(_active_governed_surfaces(worker))
    allowed_surfaces = []
    blocked_surfaces = []

    for surface_id in active_surfaces:
        if surface_id not in declared_surfaces:
            blocked_surfaces.append(
                {
                    "surface_id": surface_id,
                    "reason": "undeclared_governed_surface",
                    "pinned_adapters": [],
                }
            )
            continue
        if surface_id not in allowlisted:
            blocked_surfaces.append(
                {
                    "surface_id": surface_id,
                    "reason": "governed_surface_not_allowlisted",
                    "pinned_adapters": [],
                }
            )
            continue
        pinned_adapters = pinned_surfaces.get(surface_id, [])
        if pinned_adapters and str(worker.get("adapter_id")) not in pinned_adapters:
            blocked_surfaces.append(
                {
                    "surface_id": surface_id,
                    "reason": "governed_surface_not_pinned",
                    "pinned_adapters": pinned_adapters,
                }
            )
            continue
        allowed_surfaces.append({"surface_id": surface_id})

    return {
        "policy_version": governance_policy.get("policy_version"),
        "workflow_class": workflow_class,
        "active_surfaces": active_surfaces,
        "allowed_surfaces": allowed_surfaces,
        "blocked_surfaces": blocked_surfaces,
        "eligible": not blocked_surfaces,
    }


def governance_rejection_reasons(governance_summary: dict[str, object]) -> list[str]:
    reasons = []
    for blocked in governance_summary.get("blocked_surfaces", []):
        surface_id = str(blocked.get("surface_id"))
        reason = str(blocked.get("reason"))
        reasons.append(f"{reason}:{surface_id}")
    return reasons


def apply_audit_content_policy(
    governance_policy: dict[str, object],
    *,
    rich_content: dict[str, object],
) -> tuple[dict[str, object], str]:
    governed_content: dict[str, object] = {}
    redaction_level = "none"
    audit_policy = governance_policy.get("audit_content", {})
    for content_kind, value in rich_content.items():
        mode = str(audit_policy.get(content_kind, {}).get("mode", "omit"))
        if mode not in AUDIT_CONTENT_RETENTION_MODES:
            mode = "omit"
        if mode == "retain":
            governed_content[content_kind] = {"status": "retained", "value": value}
            continue
        if mode == "redact":
            governed_content[content_kind] = {"status": "redacted"}
            redaction_level = "redacted"
            continue
        governed_content[content_kind] = {"status": "omitted"}
        if redaction_level == "none":
            redaction_level = "omitted"
    return governed_content, redaction_level


def _active_governed_surfaces(worker: dict[str, object]) -> list[str]:
    surfaces = []
    for tag in _load_string_list(worker.get("operator_tags")):
        if tag.startswith(GOVERNED_SURFACE_TAG_PREFIX):
            surfaces.append(tag[len(GOVERNED_SURFACE_TAG_PREFIX) :])
    return surfaces


def _load_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _load_surface_pin_map(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {str(key): sorted(str(item) for item in _load_string_list(items)) for key, items in value.items()}
