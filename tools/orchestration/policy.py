#!/usr/bin/env python3
"""Repo-local routing and governance policy bootstrap plus policy helpers."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import re
import shlex
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.config import adapter_secret_source_paths, adapter_settings_path, load_adapter_settings
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

DEFAULT_OPERATING_PROFILE = "primary_plus_fallback"
SURFACE_VERSION_PIN_SELECTOR_ANY = "*"

DEFAULT_GOVERNANCE_POLICY = {
    "policy_version": "phase1-governance-v1",
    "operating_profile": DEFAULT_OPERATING_PROFILE,
    "governed_surfaces": {
        "allowlisted_surfaces": [],
        "pinned_surfaces": {},
    },
    "secret_scopes": [],
    "surface_version_pins": [],
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
SECRET_SCOPE_REDACTION_DEFAULT = "redacted"
TRUSTED_SURFACE_VERSION_CONFIDENCE = {"medium", "high"}
SURFACE_VERSION_MAX_FRESHNESS_SECONDS = 60
SURFACE_VERSION_REASON_PRIORITY = {
    "surface_version_evidence_stale": 0,
    "surface_version_evidence_untrusted": 1,
    "surface_version_evidence_missing": 2,
    "surface_version_pin_mismatch": 3,
}
SECRET_RESOLUTION_REASON_NO_MATCH = "secret_scope_no_match"
SECRET_RESOLUTION_REASON_SELECTOR_MISMATCH = "secret_scope_selector_mismatch"
SECRET_RESOLUTION_REASON_UNRESOLVED_REF = "secret_ref_unresolved"
SECRET_DELIVERY_MODE_PRELOADED_WORKER_ENV = "preloaded_worker_env"
SECRET_SCOPE_ALLOWED_INPUT_FIELDS = frozenset(
    {
        "surface_id",
        "adapter_id",
        "workflow_class",
        "operating_profile",
        "secret_ref",
        "secret_reference",
        "display_name",
        "display_label",
        "display_hint",
        "redaction_label",
        "redaction_marker",
        "redaction_mode",
    }
)


@dataclass(frozen=True)
class DecisionRightsSpec:
    action_key: str
    decision_class: str
    confirmation_required: bool
    supported: bool
    policy_message: str
    checkpoint_eligible: bool = False


DECISION_RIGHTS_SPECS = {
    "task.close": DecisionRightsSpec(
        action_key="task.close",
        decision_class="policy_automatic",
        confirmation_required=False,
        supported=True,
        policy_message="controller executed task close within policy-automatic bounds",
        checkpoint_eligible=True,
    ),
    "task.archive": DecisionRightsSpec(
        action_key="task.archive",
        decision_class="policy_automatic",
        confirmation_required=False,
        supported=True,
        policy_message="controller executed task archive within policy-automatic bounds",
        checkpoint_eligible=True,
    ),
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


class GovernancePolicyValidationError(RuntimeError):
    """Raised when governance policy content violates controller-owned schema rules."""


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
        payload_normalizer=lambda payload: normalize_governance_policy(
            _sanitize_governance_policy_secret_scopes(payload)
        ),
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
    payload_normalizer: Callable[[dict[str, object]], dict[str, object]] | None = None,
) -> _SinglePolicyBootstrapResult:
    policy_created = not policy_path.exists()
    if policy_created:
        policy_path.write_text(json.dumps(default_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    policy = _load_policy(policy_path)
    snapshot_payload = payload_normalizer(dict(policy)) if payload_normalizer is not None else dict(policy)
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
                    json.dumps(snapshot_payload, sort_keys=True),
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


def load_governance_policy(
    policy_path: Path,
    *,
    persist_sanitized: bool = True,
) -> dict[str, object]:
    if persist_sanitized:
        sanitize_governance_policy_file(policy_path)
        governance_policy = _load_policy(policy_path)
    else:
        governance_policy = _sanitize_governance_policy_secret_scopes(_load_policy(policy_path))
    return normalize_governance_policy(governance_policy)


def _load_policy(policy_path: Path) -> dict[str, object]:
    return json.loads(policy_path.read_text(encoding="utf-8"))


def normalize_governance_policy(governance_policy: dict[str, object]) -> dict[str, object]:
    normalized = dict(governance_policy)
    operating_profile = _normalize_operating_profile(governance_policy.get("operating_profile"))
    normalized["operating_profile"] = operating_profile
    normalized["secret_scopes"] = _normalize_secret_scopes(
        governance_policy.get("secret_scopes"),
        operating_profile=operating_profile,
    )
    normalized["surface_version_pins"] = _normalize_surface_version_pins(
        governance_policy.get("surface_version_pins"),
        operating_profile=operating_profile,
    )
    return normalized


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


def resolve_surface_version_pins(
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
    operating_profile: str | None = None,
    adapter_id: str | None = None,
    surface_id: str | None = None,
    surface_ids: list[str] | None = None,
) -> dict[str, object]:
    normalized_policy = normalize_governance_policy(governance_policy)
    active_profile = _normalize_operating_profile(operating_profile or normalized_policy.get("operating_profile"))
    normalized_pins = _normalize_surface_version_pins(
        normalized_policy.get("surface_version_pins"),
        operating_profile=active_profile,
    )
    applicable_surface_ids = _normalize_surface_ids(surface_ids)
    if applicable_surface_ids is not None:
        normalized_pins = [
            dict(pin)
            for pin in normalized_pins
            if str(pin.get("surface_id", "")) in applicable_surface_ids
        ]

    effective_pins = []
    for pin in normalized_pins:
        if not _selector_matches(str(pin.get("surface_id", "")), surface_id):
            continue
        if not _selector_matches(str(pin.get("adapter_id", SURFACE_VERSION_PIN_SELECTOR_ANY)), adapter_id):
            continue
        if not _selector_matches(str(pin.get("workflow_class", SURFACE_VERSION_PIN_SELECTOR_ANY)), workflow_class):
            continue
        if not _selector_matches(str(pin.get("operating_profile", active_profile)), active_profile):
            continue
        effective_pins.append(dict(pin))

    state = "configured" if normalized_pins else "none_configured"
    if not normalized_pins:
        effective_state = "none_configured"
    elif effective_pins:
        effective_state = "pins_apply"
    else:
        effective_state = "no_matching_pins"

    return {
        "operating_profile": active_profile,
        "state": state,
        "effective_state": effective_state,
        "normalized_pins": normalized_pins,
        "effective_pins": effective_pins,
    }


def resolve_secret_scopes(
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
    operating_profile: str | None = None,
    adapter_id: str | None = None,
    surface_id: str | None = None,
    surface_ids: list[str] | None = None,
) -> dict[str, object]:
    normalized_policy = normalize_governance_policy(governance_policy)
    active_profile = _normalize_operating_profile(operating_profile or normalized_policy.get("operating_profile"))
    normalized_scopes = _normalize_secret_scopes(
        normalized_policy.get("secret_scopes"),
        operating_profile=active_profile,
    )
    applicable_surface_ids = _normalize_surface_ids(surface_ids)
    if applicable_surface_ids is not None:
        normalized_scopes = [
            dict(scope)
            for scope in normalized_scopes
            if _scope_matches_surface_context(
                str(scope.get("surface_id", SURFACE_VERSION_PIN_SELECTOR_ANY)),
                applicable_surface_ids,
            )
        ]

    effective_scopes = []
    for scope in normalized_scopes:
        if not _selector_matches(str(scope.get("surface_id", SURFACE_VERSION_PIN_SELECTOR_ANY)), surface_id):
            continue
        if not _selector_matches(str(scope.get("adapter_id", SURFACE_VERSION_PIN_SELECTOR_ANY)), adapter_id):
            continue
        if not _selector_matches(str(scope.get("workflow_class", SURFACE_VERSION_PIN_SELECTOR_ANY)), workflow_class):
            continue
        if not _selector_matches(str(scope.get("operating_profile", active_profile)), active_profile):
            continue
        effective_scopes.append(dict(scope))

    state = "configured" if normalized_scopes else "none_configured"
    if not normalized_scopes:
        effective_state = "none_configured"
    elif effective_scopes:
        effective_state = "scopes_apply"
    else:
        effective_state = "no_matching_scopes"

    return {
        "operating_profile": active_profile,
        "state": state,
        "effective_state": effective_state,
        "normalized_scopes": normalized_scopes,
        "effective_scopes": effective_scopes,
    }


def evaluate_action_secret_resolution(
    governance_policy: dict[str, object],
    *,
    repo_root: Path,
    adapter_descriptor: dict[str, object],
    adapter_id: str,
    workflow_class: str,
    operating_profile: str | None = None,
    surface_ids: list[str] | None = None,
) -> dict[str, object]:
    """Resolve only the selected governed surfaces that explicitly require secret-backed execution."""

    normalized_policy = normalize_governance_policy(governance_policy)
    active_profile = _normalize_operating_profile(operating_profile or normalized_policy.get("operating_profile"))
    required_surfaces = [
        {
            "surface_id": surface_id,
            "delivery_mode": str(requirements.get("delivery_mode") or SECRET_DELIVERY_MODE_PRELOADED_WORKER_ENV),
        }
        for surface_id, requirements in sorted(_governed_surface_requirements(adapter_descriptor).items())
        if bool(requirements.get("requires_secret")) and (surface_ids is None or surface_id in set(surface_ids))
    ]
    audit_summary = {
        "status": "not_required",
        "eligible": True,
        "adapter_id": adapter_id,
        "workflow_class": workflow_class,
        "operating_profile": active_profile,
        "required_surface_ids": [item["surface_id"] for item in required_surfaces],
        "required_secret_refs": [],
        "resolved_secret_refs": [],
        "surface_summaries": [],
        "reason": None,
        "delivery_mode": required_surfaces[0]["delivery_mode"] if required_surfaces else None,
        "redaction_level": "ref_only",
    }
    if not required_surfaces:
        return {
            "eligible": True,
            "audit_summary": audit_summary,
            "dispatch_secret_context": None,
            "secret_source_paths": [],
        }

    adapter_settings = load_adapter_settings(adapter_settings_path(repo_root / ".codex" / "orchestration"))
    secret_source_paths = adapter_secret_source_paths(repo_root, adapter_settings, adapter_id)
    file_env_cache: dict[str, dict[str, str]] = {}
    resolved_secret_values: dict[str, str] = {}
    blocked_surfaces: list[dict[str, object]] = []

    for required_surface in required_surfaces:
        surface_id = required_surface["surface_id"]
        selector_context = {
            "surface_id": surface_id,
            "adapter_id": adapter_id,
            "workflow_class": workflow_class,
            "operating_profile": active_profile,
        }
        scope_summary = resolve_secret_scopes(
            normalized_policy,
            workflow_class=workflow_class,
            operating_profile=active_profile,
            adapter_id=adapter_id,
            surface_id=surface_id,
        )
        required_secret_refs = sorted(
            {
                str(scope["secret_ref"])
                for scope in scope_summary["effective_scopes"]
                if isinstance(scope, dict) and scope.get("secret_ref")
            }
        )
        surface_summary = {
            "surface_id": surface_id,
            "selector_context": selector_context,
            "requires_secret": True,
            "delivery_mode": required_surface["delivery_mode"],
            "scope_state": scope_summary["effective_state"],
            "applicable_scopes": [dict(scope) for scope in scope_summary["effective_scopes"]],
            "required_secret_refs": required_secret_refs,
            "resolved_secret_refs": [],
            "unresolved_secret_refs": [],
            "reason": None,
        }
        if not scope_summary["effective_scopes"]:
            if not _surface_has_configured_secret_scope(scope_summary["normalized_scopes"], surface_id):
                audit_summary["surface_summaries"].append(surface_summary)
                continue
            surface_summary["reason"] = _secret_scope_failure_reason(
                scope_summary["normalized_scopes"],
                selector_context=selector_context,
            )
            blocked_surfaces.append(surface_summary)
            audit_summary["surface_summaries"].append(surface_summary)
            continue

        for secret_ref in required_secret_refs:
            secret_value = _resolve_secret_ref_from_local_sources(
                secret_ref,
                secret_source_paths=secret_source_paths,
                environment=os.environ,
                file_env_cache=file_env_cache,
            )
            if secret_value is None:
                surface_summary["reason"] = SECRET_RESOLUTION_REASON_UNRESOLVED_REF
                surface_summary["unresolved_secret_refs"].append(secret_ref)
                continue
            surface_summary["resolved_secret_refs"].append(secret_ref)
            resolved_secret_values[secret_ref] = secret_value

        if surface_summary["unresolved_secret_refs"]:
            blocked_surfaces.append(surface_summary)

        audit_summary["surface_summaries"].append(surface_summary)

    required_secret_refs = sorted(
        {
            secret_ref
            for surface_summary in audit_summary["surface_summaries"]
            for secret_ref in surface_summary["required_secret_refs"]
        }
    )
    resolved_secret_refs = sorted(
        {
            secret_ref
            for surface_summary in audit_summary["surface_summaries"]
            for secret_ref in surface_summary["resolved_secret_refs"]
        }
    )
    audit_summary["required_secret_refs"] = required_secret_refs
    audit_summary["resolved_secret_refs"] = resolved_secret_refs
    if blocked_surfaces:
        audit_summary["status"] = "blocked"
        audit_summary["eligible"] = False
        audit_summary["reason"] = str(blocked_surfaces[0]["reason"])
        return {
            "eligible": False,
            "audit_summary": audit_summary,
            "dispatch_secret_context": None,
            "secret_source_paths": [str(path) for path in secret_source_paths],
        }

    if not required_secret_refs:
        return {
            "eligible": True,
            "audit_summary": audit_summary,
            "dispatch_secret_context": None,
            "secret_source_paths": [str(path) for path in secret_source_paths],
        }

    audit_summary["status"] = "resolved"
    return {
        "eligible": True,
        "audit_summary": audit_summary,
        "dispatch_secret_context": {
            "delivery_mode": str(audit_summary["delivery_mode"] or SECRET_DELIVERY_MODE_PRELOADED_WORKER_ENV),
            "secret_refs": resolved_secret_refs,
            # Raw values stay in-memory and are only forwarded to the adapter dispatch call.
            "resolved_secrets": [
                {"secret_ref": secret_ref, "value": resolved_secret_values[secret_ref]}
                for secret_ref in resolved_secret_refs
            ],
        },
        "secret_source_paths": [str(path) for path in secret_source_paths],
    }


def secret_resolution_blocking_condition(secret_resolution: dict[str, object]) -> str | None:
    if not isinstance(secret_resolution, dict) or secret_resolution.get("status") != "blocked":
        return None
    blocked_surface = _first_blocked_secret_surface(secret_resolution)
    if blocked_surface is None:
        return "secret-scope enforcement blocked the selected governed action"
    surface_id = str(blocked_surface.get("surface_id") or "unknown")
    reason = str(blocked_surface.get("reason") or "")
    if reason == SECRET_RESOLUTION_REASON_NO_MATCH:
        return (
            f"secret-scope enforcement blocked governed surface {surface_id}: "
            "no matching secret scope is configured for the selected adapter, workflow, and operating profile"
        )
    if reason == SECRET_RESOLUTION_REASON_SELECTOR_MISMATCH:
        return (
            f"secret-scope enforcement blocked governed surface {surface_id}: "
            "configured secret scopes did not match the selected adapter, workflow, or operating profile"
        )
    secret_ref = _first_surface_secret_ref(blocked_surface)
    if secret_ref is not None:
        return (
            f"secret-scope enforcement blocked governed surface {surface_id}: "
            f"required secret ref {secret_ref} could not be resolved from the local operator-managed env seam"
        )
    return f"secret-scope enforcement blocked governed surface {surface_id}"


def secret_resolution_next_action(
    *,
    task_id: str,
    secret_resolution: dict[str, object],
    governance_policy_path: str | None,
    secret_source_paths: list[str] | None,
) -> str | None:
    if not isinstance(secret_resolution, dict) or secret_resolution.get("status") != "blocked":
        return None
    blocked_surface = _first_blocked_secret_surface(secret_resolution)
    if blocked_surface is None:
        return f"inspect the selected governed action for task {task_id} before retrying"
    policy_ref = governance_policy_path or "governance policy"
    source_ref = next((path for path in secret_source_paths or [] if path), "the local worker env seam")
    surface_id = str(blocked_surface.get("surface_id") or "unknown")
    reason = str(blocked_surface.get("reason") or "")
    if reason in {SECRET_RESOLUTION_REASON_NO_MATCH, SECRET_RESOLUTION_REASON_SELECTOR_MISMATCH}:
        return f"review {policy_ref}, add a matching secret scope for surface {surface_id}, then retry task {task_id}"
    secret_ref = _first_surface_secret_ref(blocked_surface) or "the required secret ref"
    return (
        f"review {policy_ref} and {source_ref}, make {secret_ref} available through the selected worker env seam, "
        f"then retry task {task_id}"
    )


def active_policy_snapshot(state_db: Path, *, metadata_key: str) -> dict[str, object] | None:
    conn = connect_state_db(state_db)
    try:
        metadata_row = conn.execute("SELECT value FROM metadata WHERE key = ?", (metadata_key,)).fetchone()
        if metadata_row is None:
            return None
        snapshot_row = conn.execute(
            """
            SELECT snapshot_id, policy_origin, policy_version, captured_at
                   , payload
            FROM policy_snapshots
            WHERE snapshot_id = ?
            """,
            (metadata_row["value"],),
        ).fetchone()
    finally:
        conn.close()
    if snapshot_row is None:
        return {
            "snapshot_id": metadata_row["value"],
            "traceability_status": "snapshot_record_missing",
        }
    snapshot = {
        "snapshot_id": snapshot_row["snapshot_id"],
        "policy_origin": snapshot_row["policy_origin"],
        "policy_version": snapshot_row["policy_version"],
        "captured_at": snapshot_row["captured_at"],
    }
    payload = _load_snapshot_payload(snapshot_row["payload"])
    if payload is not None:
        snapshot["payload"] = payload
    return snapshot


def active_governance_snapshot(
    state_db: Path,
    *,
    live_policy: dict[str, object] | None = None,
    workflow_class: str | None = None,
    operating_profile: str | None = None,
    adapter_id: str | None = None,
    surface_id: str | None = None,
    surface_ids: list[str] | None = None,
) -> dict[str, object] | None:
    snapshot = active_policy_snapshot(state_db, metadata_key="active_governance_policy_snapshot_id")
    if snapshot is None:
        return None
    payload = snapshot.pop("payload", None)
    if not isinstance(payload, dict):
        return snapshot

    snapshot_policy = normalize_governance_policy(payload)
    live_policy_normalized = normalize_governance_policy(live_policy) if isinstance(live_policy, dict) else None
    active_profile = _normalize_operating_profile(
        operating_profile
        or (live_policy_normalized or {}).get("operating_profile")
        or snapshot_policy.get("operating_profile")
    )
    snapshot["operating_profile"] = active_profile
    snapshot["secret_scopes"] = resolve_secret_scopes(
        snapshot_policy,
        workflow_class=workflow_class,
        operating_profile=active_profile,
        adapter_id=adapter_id,
        surface_id=surface_id,
        surface_ids=surface_ids,
    )
    snapshot["surface_version_pins"] = resolve_surface_version_pins(
        snapshot_policy,
        workflow_class=workflow_class,
        operating_profile=active_profile,
        adapter_id=adapter_id,
        surface_id=surface_id,
        surface_ids=surface_ids,
    )
    if live_policy_normalized is None:
        snapshot["traceability_status"] = "snapshot_only"
        return snapshot

    matches_live_policy = snapshot_policy == live_policy_normalized
    snapshot["matches_live_policy"] = matches_live_policy
    snapshot["traceability_status"] = "matches_live_policy" if matches_live_policy else "stale_vs_live_policy"
    return snapshot


def describe_adapter_governance(
    adapter_descriptor: dict[str, object],
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
) -> dict[str, object]:
    normalized_policy = normalize_governance_policy(governance_policy)
    effective_policy = effective_surface_policy(normalized_policy, workflow_class=workflow_class)
    declared_surfaces = []
    declared_surface_ids = _load_string_list(adapter_descriptor.get("governed_surfaces"))
    surface_requirements = _governed_surface_requirements(adapter_descriptor)
    allowlisted = set(effective_policy["allowlisted_surfaces"])
    pinned_surfaces = effective_policy["pinned_surfaces"]
    adapter_id = str(adapter_descriptor["adapter_id"])
    secret_scope_summary = resolve_secret_scopes(
        normalized_policy,
        workflow_class=workflow_class,
        adapter_id=adapter_id,
        surface_ids=declared_surface_ids,
    )
    version_pin_summary = resolve_surface_version_pins(
        normalized_policy,
        workflow_class=workflow_class,
        adapter_id=adapter_id,
        surface_ids=declared_surface_ids,
    )
    for surface_id in declared_surface_ids:
        declared_surfaces.append(
            {
                "surface_id": surface_id,
                "allowlisted": surface_id in allowlisted,
                "requires_secret": bool(surface_requirements.get(surface_id, {}).get("requires_secret")),
                "secret_delivery_mode": surface_requirements.get(surface_id, {}).get("delivery_mode"),
                "pinned_adapters": pinned_surfaces.get(surface_id, []),
                "applicable_secret_scopes": resolve_secret_scopes(
                    normalized_policy,
                    workflow_class=workflow_class,
                    adapter_id=adapter_id,
                    surface_id=surface_id,
                )["effective_scopes"],
                "applicable_version_pins": resolve_surface_version_pins(
                    normalized_policy,
                    workflow_class=workflow_class,
                    adapter_id=adapter_id,
                    surface_id=surface_id,
                )["effective_pins"],
            }
        )
    return {
        "policy_version": normalized_policy.get("policy_version"),
        "workflow_class": workflow_class,
        "operating_profile": normalized_policy.get("operating_profile"),
        "declared_surfaces": declared_surfaces,
        "secret_scopes": secret_scope_summary,
        "surface_version_pins": version_pin_summary,
    }


def evaluate_surface_version_evidence(
    worker: dict[str, object],
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
    operating_profile: str | None = None,
    surface_ids: list[str] | None = None,
    adapter_evidence: list[dict[str, object]] | None = None,
    enforce: bool = False,
) -> dict[str, object]:
    normalized_policy = normalize_governance_policy(governance_policy)
    active_profile = _normalize_operating_profile(operating_profile or normalized_policy.get("operating_profile"))
    summary = resolve_surface_version_pins(
        normalized_policy,
        workflow_class=workflow_class,
        operating_profile=active_profile,
        adapter_id=str(worker.get("adapter_id") or ""),
        surface_ids=surface_ids,
    )
    summary["workflow_class"] = workflow_class
    summary["eligible"] = True
    summary["probe_required"] = False
    summary["evaluation_state"] = "not_applicable"
    summary["evaluated_surfaces"] = []
    summary["blocked_surfaces"] = []
    summary["observed"] = {
        "runtime_identity": _observed_runtime_identity(adapter_evidence),
        "model_identity": _observed_model_identity(adapter_evidence),
    }
    if summary["effective_state"] != "pins_apply":
        return summary

    if not enforce and adapter_evidence is None:
        summary["probe_required"] = True
        summary["evaluation_state"] = "probe_required"
        return summary

    summary["evaluation_state"] = "evaluated"
    pins_by_surface: dict[str, list[dict[str, str | None]]] = {}
    for pin in summary["effective_pins"]:
        surface_id = str(pin.get("surface_id") or "")
        if not surface_id:
            continue
        pins_by_surface.setdefault(surface_id, []).append(dict(pin))

    runtime_observation = summary["observed"]["runtime_identity"]
    model_observation = summary["observed"]["model_identity"]
    for surface_id in sorted(pins_by_surface):
        applicable_pins = pins_by_surface[surface_id]
        pin_results = [
            _evaluate_surface_version_pin(
                pin,
                runtime_observation=runtime_observation,
                model_observation=model_observation,
            )
            for pin in applicable_pins
        ]
        failure_reasons = sorted(
            {
                reason
                for pin_result in pin_results
                for reason in pin_result.get("failure_reasons", [])
            },
            key=_surface_version_reason_sort_key,
        )
        selector_context = {
            "surface_id": surface_id,
            "adapter_id": str(worker.get("adapter_id") or ""),
            "workflow_class": workflow_class,
            "operating_profile": active_profile,
        }
        evaluated_surface = {
            "surface_id": surface_id,
            "selector_context": selector_context,
            "applicable_pins": applicable_pins,
            "observed": {
                "runtime_identity": runtime_observation,
                "model_identity": model_observation,
            },
            "pin_results": pin_results,
            "eligible": not failure_reasons,
        }
        summary["evaluated_surfaces"].append(evaluated_surface)
        if failure_reasons:
            summary["blocked_surfaces"].append(
                {
                    **evaluated_surface,
                    "reason": _primary_surface_version_reason(failure_reasons),
                    "failure_reasons": failure_reasons,
                }
            )

    summary["eligible"] = not summary["blocked_surfaces"]
    return summary


def evaluate_worker_governance(
    worker: dict[str, object],
    adapter_descriptor: dict[str, object],
    governance_policy: dict[str, object],
    *,
    workflow_class: str | None = None,
    adapter_evidence: list[dict[str, object]] | None = None,
    enforce_surface_version_pins: bool = False,
    registration_scope: bool = False,
) -> dict[str, object]:
    normalized_policy = normalize_governance_policy(governance_policy)
    effective_policy = effective_surface_policy(normalized_policy, workflow_class=workflow_class)
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

    version_pin_summary = evaluate_surface_version_evidence(
        worker,
        normalized_policy,
        workflow_class=SURFACE_VERSION_PIN_SELECTOR_ANY if registration_scope else workflow_class,
        operating_profile=str(normalized_policy.get("operating_profile") or DEFAULT_OPERATING_PROFILE),
        surface_ids=[surface["surface_id"] for surface in allowed_surfaces],
        adapter_evidence=adapter_evidence,
        enforce=enforce_surface_version_pins,
    )
    blocked_surface_ids = {str(item.get("surface_id") or "") for item in version_pin_summary.get("blocked_surfaces", [])}
    if blocked_surface_ids:
        allowed_surfaces = [
            surface for surface in allowed_surfaces if str(surface.get("surface_id") or "") not in blocked_surface_ids
        ]
        blocked_surfaces.extend(version_pin_summary["blocked_surfaces"])

    return {
        "policy_version": normalized_policy.get("policy_version"),
        "workflow_class": workflow_class,
        "operating_profile": normalized_policy.get("operating_profile"),
        "active_surfaces": active_surfaces,
        "allowed_surfaces": allowed_surfaces,
        "blocked_surfaces": blocked_surfaces,
        "surface_version_pins": version_pin_summary,
        "eligible": not blocked_surfaces,
    }


def governance_rejection_reasons(governance_summary: dict[str, object]) -> list[str]:
    reasons = []
    for blocked in governance_summary.get("blocked_surfaces", []):
        surface_id = str(blocked.get("surface_id"))
        reason = str(blocked.get("reason"))
        reasons.append(f"{reason}:{surface_id}")
    return reasons


def _governed_surface_requirements(adapter_descriptor: dict[str, object]) -> dict[str, dict[str, object]]:
    requirements = adapter_descriptor.get("governed_surface_requirements")
    if not isinstance(requirements, dict):
        return {}
    return {
        str(surface_id): dict(surface_requirements)
        for surface_id, surface_requirements in requirements.items()
        if str(surface_id).strip() and isinstance(surface_requirements, dict)
    }


def _secret_scope_failure_reason(
    normalized_scopes: list[dict[str, str | None]],
    *,
    selector_context: dict[str, str],
) -> str:
    surface_id = selector_context["surface_id"]
    for scope in normalized_scopes:
        if not _selector_matches(str(scope.get("surface_id", SURFACE_VERSION_PIN_SELECTOR_ANY)), surface_id):
            continue
        return SECRET_RESOLUTION_REASON_SELECTOR_MISMATCH
    return SECRET_RESOLUTION_REASON_NO_MATCH


def _surface_has_configured_secret_scope(
    normalized_scopes: list[dict[str, str | None]],
    surface_id: str,
) -> bool:
    return any(
        _selector_matches(str(scope.get("surface_id", SURFACE_VERSION_PIN_SELECTOR_ANY)), surface_id)
        for scope in normalized_scopes
    )


def _resolve_secret_ref_from_local_sources(
    secret_ref: str,
    *,
    secret_source_paths: list[Path],
    environment: dict[str, str],
    file_env_cache: dict[str, dict[str, str]],
) -> str | None:
    for env_key in _candidate_secret_env_keys(secret_ref):
        value = environment.get(env_key)
        if value is not None and value != "":
            return value
    for path in secret_source_paths:
        env_values = _load_env_values_from_file(path, file_env_cache)
        for env_key in _candidate_secret_env_keys(secret_ref):
            value = env_values.get(env_key)
            if value is not None and value != "":
                return value
    return None


def _candidate_secret_env_keys(secret_ref: str) -> list[str]:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", secret_ref).strip("_").upper()
    candidates = [secret_ref]
    if normalized:
        candidates.append(normalized)
    return candidates


def _load_env_values_from_file(path: Path, file_env_cache: dict[str, dict[str, str]]) -> dict[str, str]:
    marker = str(path)
    if marker in file_env_cache:
        return file_env_cache[marker]
    if not path.exists():
        file_env_cache[marker] = {}
        return file_env_cache[marker]
    env_values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        assignment = _parse_env_assignment(raw_line)
        if assignment is None:
            continue
        key, value = assignment
        env_values[key] = value
    file_env_cache[marker] = env_values
    return env_values


def _parse_env_assignment(raw_line: str) -> tuple[str, str] | None:
    stripped = raw_line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()
    if "=" not in stripped:
        return None
    key, raw_value = stripped.split("=", 1)
    key = key.strip()
    if not key or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return None
    lexer = shlex.shlex(raw_value, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = "#"
    tokens = list(lexer)
    if not tokens:
        return key, ""
    return key, " ".join(tokens)


def _first_blocked_secret_surface(secret_resolution: dict[str, object]) -> dict[str, object] | None:
    for surface_summary in secret_resolution.get("surface_summaries", []):
        if isinstance(surface_summary, dict) and surface_summary.get("reason"):
            return surface_summary
    return None


def _first_surface_secret_ref(surface_summary: dict[str, object]) -> str | None:
    for key in ("unresolved_secret_refs", "required_secret_refs", "resolved_secret_refs"):
        values = surface_summary.get(key) or []
        if values:
            return str(values[0])
    for scope in surface_summary.get("applicable_scopes", []):
        if isinstance(scope, dict) and scope.get("secret_ref"):
            return str(scope["secret_ref"])
    return None


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


def _normalize_operating_profile(value: object) -> str:
    if value is None:
        return DEFAULT_OPERATING_PROFILE
    text = str(value).strip()
    return text or DEFAULT_OPERATING_PROFILE


def _normalize_surface_version_pins(
    value: object,
    *,
    operating_profile: str,
) -> list[dict[str, str | None]]:
    if not isinstance(value, list):
        return []

    normalized = []
    for raw_pin in value:
        if not isinstance(raw_pin, dict):
            continue
        surface_id = str(raw_pin.get("surface_id", "")).strip()
        if not surface_id:
            continue
        expected_runtime_identity = _normalize_optional_string(raw_pin.get("expected_runtime_identity"))
        expected_model_identity = _normalize_optional_string(raw_pin.get("expected_model_identity"))
        if expected_runtime_identity is None and expected_model_identity is None:
            continue
        normalized.append(
            {
                "surface_id": surface_id,
                "adapter_id": _normalize_selector(raw_pin.get("adapter_id")),
                "workflow_class": _normalize_selector(raw_pin.get("workflow_class")),
                "operating_profile": _normalize_selector(
                    raw_pin.get("operating_profile"),
                    default=operating_profile,
                ),
                "expected_runtime_identity": expected_runtime_identity,
                "expected_model_identity": expected_model_identity,
            }
        )
    normalized.sort(
        key=lambda item: (
            str(item["surface_id"]),
            str(item["adapter_id"]),
            str(item["workflow_class"]),
            str(item["operating_profile"]),
            str(item["expected_runtime_identity"] or ""),
            str(item["expected_model_identity"] or ""),
        )
    )
    return normalized


def _normalize_secret_scopes(
    value: object,
    *,
    operating_profile: str,
) -> list[dict[str, str | None]]:
    if not isinstance(value, list):
        return []

    normalized = []
    for index, raw_scope in enumerate(value):
        if not isinstance(raw_scope, dict):
            continue
        unsupported_fields = _unsupported_secret_scope_fields(raw_scope)
        if unsupported_fields:
            field_list = ", ".join(sorted(unsupported_fields))
            raise GovernancePolicyValidationError(
                f"secret_scopes[{index}] contains unsupported field(s): {field_list}; "
                "only selector, secret reference, and audit-safe display/redaction metadata are allowed"
            )
        secret_ref = _first_nonempty_string(
            raw_scope.get("secret_ref"),
            raw_scope.get("secret_reference"),
        )
        if secret_ref is None:
            continue
        normalized.append(
            {
                "surface_id": _normalize_selector(raw_scope.get("surface_id")),
                "adapter_id": _normalize_selector(raw_scope.get("adapter_id")),
                "workflow_class": _normalize_selector(raw_scope.get("workflow_class")),
                "operating_profile": _normalize_selector(
                    raw_scope.get("operating_profile"),
                    default=operating_profile,
                ),
                "secret_ref": secret_ref,
                "display_name": _first_nonempty_string(
                    raw_scope.get("display_name"),
                    raw_scope.get("display_label"),
                    raw_scope.get("display_hint"),
                ),
                "redaction_label": _first_nonempty_string(
                    raw_scope.get("redaction_label"),
                    raw_scope.get("redaction_marker"),
                    raw_scope.get("redaction_mode"),
                )
                or SECRET_SCOPE_REDACTION_DEFAULT,
            }
        )
    normalized.sort(
        key=lambda item: (
            str(item["surface_id"]),
            str(item["adapter_id"]),
            str(item["workflow_class"]),
            str(item["operating_profile"]),
            str(item["secret_ref"]),
            str(item["display_name"] or ""),
            str(item["redaction_label"] or ""),
        )
    )
    return normalized


def _normalize_selector(value: object, *, default: str = SURFACE_VERSION_PIN_SELECTOR_ANY) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _normalize_optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_nonempty_string(*values: object) -> str | None:
    for value in values:
        text = _normalize_optional_string(value)
        if text is not None:
            return text
    return None


def sanitize_governance_policy_file(policy_path: Path) -> bool:
    if not policy_path.exists():
        return False
    governance_policy = _load_policy(policy_path)
    sanitized_policy = _sanitize_governance_policy_secret_scopes(governance_policy)
    if sanitized_policy == governance_policy:
        return False
    policy_path.write_text(json.dumps(sanitized_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def _sanitize_governance_policy_secret_scopes(governance_policy: dict[str, object]) -> dict[str, object]:
    raw_scopes = governance_policy.get("secret_scopes")
    if not isinstance(raw_scopes, list):
        return governance_policy

    changed = False
    sanitized_scopes = []
    for raw_scope in raw_scopes:
        if not isinstance(raw_scope, dict):
            sanitized_scopes.append(raw_scope)
            continue
        sanitized_scope = {
            key: value
            for key, value in raw_scope.items()
            if _is_allowed_secret_scope_field(key)
        }
        if sanitized_scope != raw_scope:
            changed = True
        sanitized_scopes.append(sanitized_scope)

    if not changed:
        return governance_policy
    sanitized_policy = dict(governance_policy)
    sanitized_policy["secret_scopes"] = sanitized_scopes
    return sanitized_policy


def _unsupported_secret_scope_fields(raw_scope: dict[object, object]) -> list[str]:
    return [
        str(key)
        for key in raw_scope
        if not _is_allowed_secret_scope_field(key)
    ]


def _is_allowed_secret_scope_field(key: object) -> bool:
    return str(key).strip() in SECRET_SCOPE_ALLOWED_INPUT_FIELDS


def _normalize_surface_ids(value: list[str] | None) -> set[str] | None:
    if value is None:
        return None
    surface_ids = {str(item).strip() for item in value if str(item).strip()}
    return surface_ids


def _selector_matches(selector: str, actual: str | None) -> bool:
    if actual is None:
        return True
    return selector == SURFACE_VERSION_PIN_SELECTOR_ANY or selector == actual


def _scope_matches_surface_context(selector: str, surface_ids: set[str]) -> bool:
    if not surface_ids:
        return False
    if selector == SURFACE_VERSION_PIN_SELECTOR_ANY:
        return True
    return selector in surface_ids


def _evaluate_surface_version_pin(
    pin: dict[str, str | None],
    *,
    runtime_observation: dict[str, object] | None,
    model_observation: dict[str, object] | None,
) -> dict[str, object]:
    checks = []
    failure_reasons = []
    expected_runtime_identity = pin.get("expected_runtime_identity")
    if expected_runtime_identity is not None:
        runtime_check = _evaluate_surface_version_identity(
            expected_identity=expected_runtime_identity,
            observation=runtime_observation,
        )
        checks.append({"selector": "expected_runtime_identity", **runtime_check})
        if runtime_check["reason"] is not None:
            failure_reasons.append(runtime_check["reason"])
    expected_model_identity = pin.get("expected_model_identity")
    if expected_model_identity is not None:
        model_check = _evaluate_surface_version_identity(
            expected_identity=expected_model_identity,
            observation=model_observation,
        )
        checks.append({"selector": "expected_model_identity", **model_check})
        if model_check["reason"] is not None:
            failure_reasons.append(model_check["reason"])
    return {
        "surface_id": pin.get("surface_id"),
        "selector_context": {
            "surface_id": pin.get("surface_id"),
            "adapter_id": pin.get("adapter_id"),
            "workflow_class": pin.get("workflow_class"),
            "operating_profile": pin.get("operating_profile"),
        },
        "expected": {
            "runtime_identity": expected_runtime_identity,
            "model_identity": expected_model_identity,
        },
        "observed": {
            "runtime_identity": runtime_observation,
            "model_identity": model_observation,
        },
        "checks": checks,
        "failure_reasons": sorted(set(failure_reasons), key=_surface_version_reason_sort_key),
        "eligible": not failure_reasons,
    }


def _evaluate_surface_version_identity(
    *,
    expected_identity: str,
    observation: dict[str, object] | None,
) -> dict[str, object]:
    if observation is None:
        return {
            "reason": "surface_version_evidence_missing",
            "expected_identity": expected_identity,
            "observed_identity": None,
        }
    observed_identity = _normalize_optional_string(observation.get("identity"))
    freshness_seconds = _normalize_optional_int(observation.get("freshness_seconds"))
    confidence = _normalize_optional_string(observation.get("confidence"))
    if freshness_seconds is None or freshness_seconds > SURFACE_VERSION_MAX_FRESHNESS_SECONDS:
        return {
            "reason": "surface_version_evidence_stale",
            "expected_identity": expected_identity,
            "observed_identity": observed_identity,
        }
    if confidence not in TRUSTED_SURFACE_VERSION_CONFIDENCE:
        return {
            "reason": "surface_version_evidence_untrusted",
            "expected_identity": expected_identity,
            "observed_identity": observed_identity,
        }
    if observed_identity is None or observed_identity == "unknown":
        return {
            "reason": "surface_version_evidence_missing",
            "expected_identity": expected_identity,
            "observed_identity": observed_identity,
        }
    if observed_identity != expected_identity:
        return {
            "reason": "surface_version_pin_mismatch",
            "expected_identity": expected_identity,
            "observed_identity": observed_identity,
        }
    return {
        "reason": None,
        "expected_identity": expected_identity,
        "observed_identity": observed_identity,
    }


def _observed_runtime_identity(adapter_evidence: list[dict[str, object]] | None) -> dict[str, object] | None:
    for item in adapter_evidence or []:
        if not isinstance(item, dict):
            continue
        if item.get("name") not in {"runtime_identity", "runtime_type"}:
            continue
        value = item.get("value")
        if isinstance(value, dict):
            observed_identity = _normalize_optional_string(value.get("runtime_identity") or value.get("runtime_type"))
        else:
            observed_identity = _normalize_optional_string(value)
        return {
            "identity": observed_identity,
            "freshness_seconds": _normalize_optional_int(item.get("freshness_seconds")),
            "confidence": _normalize_optional_string(item.get("confidence")),
            "source_ref": _normalize_optional_string(item.get("source_ref")),
        }
    return None


def _observed_model_identity(adapter_evidence: list[dict[str, object]] | None) -> dict[str, object] | None:
    for item in adapter_evidence or []:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if item.get("name") == "model_identity":
            observed_identity = (
                _normalize_optional_string(value.get("model_identity")) if isinstance(value, dict) else _normalize_optional_string(value)
            )
            return {
                "identity": observed_identity,
                "freshness_seconds": _normalize_optional_int(item.get("freshness_seconds")),
                "confidence": _normalize_optional_string(item.get("confidence")),
                "source_ref": _normalize_optional_string(item.get("source_ref")),
            }
        if item.get("name") == "permission_surface" and isinstance(value, dict):
            return {
                "identity": _normalize_optional_string(value.get("model")),
                "freshness_seconds": _normalize_optional_int(item.get("freshness_seconds")),
                "confidence": _normalize_optional_string(item.get("confidence")),
                "source_ref": _normalize_optional_string(item.get("source_ref")),
            }
    return None


def _normalize_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _primary_surface_version_reason(reasons: list[str]) -> str:
    if not reasons:
        return "surface_version_evidence_missing"
    return sorted(set(reasons), key=_surface_version_reason_sort_key)[0]


def _surface_version_reason_sort_key(reason: str) -> tuple[int, str]:
    return (SURFACE_VERSION_REASON_PRIORITY.get(reason, len(SURFACE_VERSION_REASON_PRIORITY)), reason)


def _load_snapshot_payload(raw_payload: object) -> dict[str, object] | None:
    if not isinstance(raw_payload, str) or not raw_payload.strip():
        return None
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload
