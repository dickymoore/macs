#!/usr/bin/env python3
"""Repo-local routing policy bootstrap and loading."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tools.orchestration.store import connect_state_db


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


DEFAULT_POLICY = {
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


@dataclass(frozen=True)
class PolicyBootstrapResult:
    policy_path_created: bool
    snapshot_created: bool
    policy_path: Path
    snapshot_id: str


def bootstrap_routing_policy(orchestration_dir: Path, state_db: Path) -> PolicyBootstrapResult:
    policy_path = orchestration_dir / "routing-policy.json"
    policy_created = not policy_path.exists()
    if policy_created:
        policy_path.write_text(json.dumps(DEFAULT_POLICY, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    policy = load_routing_policy(policy_path)
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
                ("active_policy_snapshot_id", snapshot_id),
            )
            conn.commit()
            snapshot_created = True
        else:
            snapshot_id = existing["snapshot_id"]
            snapshot_created = False
    finally:
        conn.close()

    return PolicyBootstrapResult(
        policy_path_created=policy_created,
        snapshot_created=snapshot_created,
        policy_path=policy_path,
        snapshot_id=snapshot_id,
    )


def load_routing_policy(policy_path: Path) -> dict[str, object]:
    return json.loads(policy_path.read_text(encoding="utf-8"))
