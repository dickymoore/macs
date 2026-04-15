#!/usr/bin/env python3
"""Repo-native diff/review checkpoint capture helpers."""

from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from tools.orchestration.history import latest_task_checkpoint
from tools.orchestration.policy import decision_rights_spec

TARGET_ACTION_ALIASES = {
    "archive": "task.archive",
    "close": "task.close",
    "task.archive": "task.archive",
    "task.close": "task.close",
}


@dataclass(frozen=True)
class CheckpointBundle:
    checkpoint_id: str
    captured_at: str
    evidence_refs: dict[str, str]
    baseline_fingerprint: dict[str, object]


class CheckpointCaptureError(RuntimeError):
    """Raised when repo-native checkpoint evidence cannot be captured safely."""


def normalize_target_action(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise CheckpointCaptureError("checkpoint capture requires a non-empty target action")
    action_key = TARGET_ACTION_ALIASES.get(normalized.lower(), normalized.lower())
    try:
        spec = decision_rights_spec(action_key)
    except KeyError as exc:
        raise CheckpointCaptureError(
            "checkpoint target action must be a controller-known action key; "
            "supported values are 'task.close' and 'task.archive'"
        ) from exc
    if not spec.checkpoint_eligible:
        raise CheckpointCaptureError(
            f"checkpoint target action '{spec.action_key}' is not supported in Story 2.1; "
            "supported values are 'task.close' and 'task.archive'"
        )
    return spec.action_key


def capture_review_checkpoint_bundle(
    repo_root: Path,
    checkpoints_dir: Path,
    *,
    task_id: str,
    target_action: str,
    actor_id: str,
    affected_refs: dict[str, object],
    captured_at: str,
) -> CheckpointBundle:
    repo_root = repo_root.resolve()
    normalized_target_action = normalize_target_action(target_action)
    normalized_actor_id = str(actor_id or "").strip()
    if not normalized_actor_id:
        raise CheckpointCaptureError("checkpoint capture requires attributable actor identity")

    git_top_level = Path(_git_output(repo_root, "rev-parse", "--show-toplevel").strip()).resolve()
    if git_top_level != repo_root:
        raise CheckpointCaptureError(
            f"checkpoint capture requires repo root {repo_root} to match git worktree root {git_top_level}"
        )

    head_ref = _git_output_optional(repo_root, "symbolic-ref", "-q", "HEAD")
    head_oid = _git_output_optional(repo_root, "rev-parse", "--verify", "HEAD")
    head_state = _head_state(head_ref=head_ref, head_oid=head_oid)

    status_output = _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    tracked_diff_output = _git_output(repo_root, "diff", "--no-ext-diff", "--submodule=diff", "--binary", "--no-color")
    tracked_diff_stat_output = _git_output(
        repo_root,
        "diff",
        "--no-ext-diff",
        "--submodule=diff",
        "--stat=200,120",
        "--no-color",
    )
    tracked_diff_summary_output = _git_output(
        repo_root,
        "diff",
        "--no-ext-diff",
        "--submodule=diff",
        "--summary",
        "--no-color",
    )
    staged_diff_output = _git_output(repo_root, "diff", "--cached", "--no-ext-diff", "--submodule=diff", "--binary", "--no-color")
    staged_diff_stat_output = _git_output(
        repo_root,
        "diff",
        "--cached",
        "--no-ext-diff",
        "--submodule=diff",
        "--stat=200,120",
        "--no-color",
    )
    staged_diff_summary_output = _git_output(
        repo_root,
        "diff",
        "--cached",
        "--no-ext-diff",
        "--submodule=diff",
        "--summary",
        "--no-color",
    )
    untracked_output = _git_output(repo_root, "ls-files", "--others", "--exclude-standard")
    untracked_paths = [line.strip() for line in untracked_output.splitlines() if line.strip()]
    untracked_diff_output = _build_untracked_review_artifact(repo_root, untracked_paths, "--binary", "--no-color")
    untracked_diff_stat_output = _build_untracked_review_artifact(repo_root, untracked_paths, "--stat=200,120", "--no-color")
    untracked_diff_summary_output = _build_untracked_review_artifact(repo_root, untracked_paths, "--summary", "--no-color")
    diff_output = _combine_artifact_output(tracked_diff_output, untracked_diff_output)
    diff_stat_output = _combine_artifact_output(tracked_diff_stat_output, untracked_diff_stat_output)
    diff_summary_output = _combine_artifact_output(tracked_diff_summary_output, untracked_diff_summary_output)
    status_summary = _summarize_status(status_output)

    head_artifact_name = "git-show-head.txt" if head_oid else "git-head-state.txt"
    head_artifact_output = (
        _git_output(repo_root, "show", "--stat", "--summary", "--format=fuller", "--no-patch", "HEAD")
        if head_oid
        else f"HEAD is unborn in {head_ref or 'detached/unresolved'}\n"
    )

    checkpoint_id = f"checkpoint-{uuid.uuid4().hex[:12]}"
    bundle_dir = checkpoints_dir / checkpoint_id
    evidence_refs: dict[str, str] = {}
    baseline_fingerprint = {
        "repo_root": str(repo_root),
        "git_top_level": str(git_top_level),
        "head": {
            "state": head_state,
            "oid": head_oid,
            "ref": head_ref,
        },
        "dirty_state": {
            "is_dirty": status_summary["is_dirty"],
            "tracked_change_count": status_summary["tracked_change_count"],
            "untracked_count": status_summary["untracked_count"],
        },
        "affected_paths": status_summary["affected_paths"],
        "status_digest": _text_digest(status_output),
        "diff_digest": _text_digest(diff_output),
        "staged_diff_digest": _text_digest(staged_diff_output),
        "untracked_digest": _text_digest(untracked_output),
    }
    metadata = {
        "checkpoint_id": checkpoint_id,
        "captured_at": captured_at,
        "task_id": task_id,
        "target_action": normalized_target_action,
        "actor_identity": {
            "actor_type": "operator",
            "actor_id": normalized_actor_id,
        },
        "affected_refs": dict(affected_refs),
        "baseline_fingerprint": baseline_fingerprint,
    }

    try:
        bundle_dir.mkdir(parents=True, exist_ok=False)
        evidence_refs = {
            "bundle_dir": _repo_relative_ref(repo_root, bundle_dir),
            "metadata_json": _repo_relative_ref(repo_root, bundle_dir / "metadata.json"),
            "head_ref": _repo_relative_ref(repo_root, bundle_dir / head_artifact_name),
            "git_status": _repo_relative_ref(repo_root, bundle_dir / "git-status.txt"),
            "git_untracked": _repo_relative_ref(repo_root, bundle_dir / "git-untracked.txt"),
            "git_diff": _repo_relative_ref(repo_root, bundle_dir / "git-diff.patch"),
            "git_diff_stat": _repo_relative_ref(repo_root, bundle_dir / "git-diff.stat.txt"),
            "git_diff_summary": _repo_relative_ref(repo_root, bundle_dir / "git-diff.summary.txt"),
            "git_diff_cached": _repo_relative_ref(repo_root, bundle_dir / "git-diff-cached.patch"),
            "git_diff_cached_stat": _repo_relative_ref(repo_root, bundle_dir / "git-diff-cached.stat.txt"),
            "git_diff_cached_summary": _repo_relative_ref(repo_root, bundle_dir / "git-diff-cached.summary.txt"),
        }
        metadata["evidence_refs"] = evidence_refs
        (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (bundle_dir / head_artifact_name).write_text(head_artifact_output, encoding="utf-8")
        (bundle_dir / "git-status.txt").write_text(status_output, encoding="utf-8")
        (bundle_dir / "git-untracked.txt").write_text(untracked_output, encoding="utf-8")
        (bundle_dir / "git-diff.patch").write_text(diff_output, encoding="utf-8")
        (bundle_dir / "git-diff.stat.txt").write_text(diff_stat_output, encoding="utf-8")
        (bundle_dir / "git-diff.summary.txt").write_text(diff_summary_output, encoding="utf-8")
        (bundle_dir / "git-diff-cached.patch").write_text(staged_diff_output, encoding="utf-8")
        (bundle_dir / "git-diff-cached.stat.txt").write_text(staged_diff_stat_output, encoding="utf-8")
        (bundle_dir / "git-diff-cached.summary.txt").write_text(staged_diff_summary_output, encoding="utf-8")
    except Exception as exc:
        shutil.rmtree(bundle_dir, ignore_errors=True)
        raise CheckpointCaptureError(f"failed to write checkpoint bundle {checkpoint_id}: {exc}") from exc

    return CheckpointBundle(
        checkpoint_id=checkpoint_id,
        captured_at=captured_at,
        evidence_refs=evidence_refs,
        baseline_fingerprint=baseline_fingerprint,
    )


def validate_task_checkpoint_gate(
    repo_root: Path,
    state_db: Path,
    *,
    task: dict[str, object],
    target_action: str,
) -> dict[str, object]:
    normalized_target_action = normalize_target_action(target_action)
    task_id = str(task["task_id"])
    remediation_command = f"macs task checkpoint --task {task_id} --target-action {normalized_target_action}"
    current_scope = _task_scope(task)
    latest_matching = latest_task_checkpoint(state_db, task_id, target_action=normalized_target_action)
    latest_any = latest_task_checkpoint(state_db, task_id)

    if latest_matching is None:
        if latest_any is not None:
            conflicting = _checkpoint_gate_ref(latest_any)
            return {
                "status": "blocked",
                "gate_outcome": "mismatched",
                "reason": "target_action_mismatch",
                "target_action": normalized_target_action,
                "message": (
                    f"Task {task_id} is blocked: latest checkpoint {conflicting['checkpoint_id']} targets "
                    f"{conflicting['target_action']}, not {normalized_target_action}. Run {remediation_command}."
                ),
                "remediation_command": remediation_command,
                "conflicting_checkpoint": conflicting,
            }
        return {
            "status": "blocked",
            "gate_outcome": "missing",
            "reason": "missing_checkpoint",
            "target_action": normalized_target_action,
            "message": (
                f"Task {task_id} is blocked: no current {normalized_target_action} checkpoint is recorded. "
                f"Run {remediation_command} before retrying."
            ),
            "remediation_command": remediation_command,
        }

    checkpoint = _checkpoint_gate_ref(latest_matching)
    captured_scope = latest_matching.get("affected_refs") or {}
    if captured_scope != current_scope:
        return {
            "status": "blocked",
            "gate_outcome": "stale",
            "reason": "task_scope_mismatch",
            "target_action": normalized_target_action,
            "message": (
                f"Task {task_id} is blocked: checkpoint {checkpoint['checkpoint_id']} is stale because the live task "
                f"scope no longer matches the captured task/lease/worker context. Run {remediation_command}."
            ),
            "remediation_command": remediation_command,
            "checkpoint": checkpoint,
            "mismatch_details": {
                "captured_scope": captured_scope,
                "current_scope": current_scope,
            },
        }

    current_fingerprint = current_repo_fingerprint(repo_root)
    mismatch_details = _repo_fingerprint_mismatch_details(
        latest_matching.get("baseline_fingerprint"),
        current_fingerprint,
    )
    if mismatch_details is not None:
        return {
            "status": "blocked",
            "gate_outcome": "stale",
            "reason": "repo_state_mismatch",
            "target_action": normalized_target_action,
            "message": (
                f"Task {task_id} is blocked: checkpoint {checkpoint['checkpoint_id']} is stale because repo state "
                f"no longer matches the captured baseline. Run {remediation_command}."
            ),
            "remediation_command": remediation_command,
            "checkpoint": checkpoint,
            "mismatch_details": mismatch_details,
        }

    return {
        "status": "satisfied",
        "gate_outcome": "satisfied",
        "reason": "checkpoint_current",
        "target_action": normalized_target_action,
        "message": f"Checkpoint {checkpoint['checkpoint_id']} satisfies the {normalized_target_action} gate.",
        "remediation_command": remediation_command,
        "checkpoint": checkpoint,
    }


def current_repo_fingerprint(repo_root: Path) -> dict[str, object]:
    repo_root = repo_root.resolve()
    git_top_level = Path(_git_output(repo_root, "rev-parse", "--show-toplevel").strip()).resolve()
    if git_top_level != repo_root:
        raise CheckpointCaptureError(
            f"checkpoint validation requires repo root {repo_root} to match git worktree root {git_top_level}"
        )

    head_ref = _git_output_optional(repo_root, "symbolic-ref", "-q", "HEAD")
    head_oid = _git_output_optional(repo_root, "rev-parse", "--verify", "HEAD")
    head_state = _head_state(head_ref=head_ref, head_oid=head_oid)

    status_output = _git_output(repo_root, "status", "--porcelain=v1", "--untracked-files=all")
    tracked_diff_output = _git_output(repo_root, "diff", "--no-ext-diff", "--submodule=diff", "--binary", "--no-color")
    staged_diff_output = _git_output(repo_root, "diff", "--cached", "--no-ext-diff", "--submodule=diff", "--binary", "--no-color")
    untracked_output = _git_output(repo_root, "ls-files", "--others", "--exclude-standard")
    untracked_paths = [line.strip() for line in untracked_output.splitlines() if line.strip()]
    untracked_diff_output = _build_untracked_review_artifact(repo_root, untracked_paths, "--binary", "--no-color")
    diff_output = _combine_artifact_output(tracked_diff_output, untracked_diff_output)
    status_summary = _summarize_status(status_output)

    return {
        "repo_root": str(repo_root),
        "git_top_level": str(git_top_level),
        "head": {
            "state": head_state,
            "oid": head_oid,
            "ref": head_ref,
        },
        "dirty_state": {
            "is_dirty": status_summary["is_dirty"],
            "tracked_change_count": status_summary["tracked_change_count"],
            "untracked_count": status_summary["untracked_count"],
        },
        "affected_paths": status_summary["affected_paths"],
        "status_digest": _text_digest(status_output),
        "diff_digest": _text_digest(diff_output),
        "staged_diff_digest": _text_digest(staged_diff_output),
        "untracked_digest": _text_digest(untracked_output),
    }


def _head_state(*, head_ref: str | None, head_oid: str | None) -> str:
    if head_oid and head_ref:
        return "attached"
    if head_oid and not head_ref:
        return "detached"
    if not head_oid and head_ref:
        return "unborn"
    raise CheckpointCaptureError("checkpoint capture could not determine baseline HEAD state")


def _git_output(repo_root: Path, *args: str) -> str:
    return _git_output_with_returncodes(repo_root, *args)


def _git_output_with_returncodes(
    repo_root: Path,
    *args: str,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CheckpointCaptureError("repo-native checkpoint evidence capture requires git on PATH") from exc
    if result.returncode not in allowed_returncodes:
        stderr = (result.stderr or "").strip()
        command = "git " + " ".join(args)
        raise CheckpointCaptureError(f"repo-native checkpoint evidence capture failed while running '{command}': {stderr or 'unknown git error'}")
    return result.stdout


def _git_output_optional(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CheckpointCaptureError("repo-native checkpoint evidence capture requires git on PATH") from exc
    if result.returncode == 0:
        value = result.stdout.strip()
        return value or None
    return None


def _repo_relative_ref(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def _task_scope(task: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in {
            "task_id": task["task_id"],
            "lease_id": task.get("current_lease_id"),
            "worker_id": task.get("current_worker_id"),
        }.items()
        if value is not None
    }


def _checkpoint_gate_ref(checkpoint: dict[str, object]) -> dict[str, object]:
    return {
        key: checkpoint.get(key)
        for key in (
            "checkpoint_id",
            "target_action",
            "captured_at",
            "actor_id",
            "event_id",
            "decision_event_id",
        )
        if checkpoint.get(key) is not None
    }


def _repo_fingerprint_mismatch_details(
    baseline_fingerprint: object,
    current_fingerprint: dict[str, object],
) -> dict[str, object] | None:
    if not isinstance(baseline_fingerprint, dict):
        return {
            "changed_fields": ["baseline_fingerprint"],
            "baseline": baseline_fingerprint,
            "current": current_fingerprint,
        }

    changed_fields: list[str] = []
    baseline_summary: dict[str, object] = {}
    current_summary: dict[str, object] = {}

    for key in ("repo_root", "git_top_level", "head", "dirty_state", "affected_paths"):
        baseline_value = baseline_fingerprint.get(key)
        current_value = current_fingerprint.get(key)
        if baseline_value != current_value:
            changed_fields.append(key)
            baseline_summary[key] = baseline_value
            current_summary[key] = current_value

    for key in ("status_digest", "diff_digest", "staged_diff_digest", "untracked_digest"):
        if key not in baseline_fingerprint:
            continue
        baseline_value = baseline_fingerprint.get(key)
        current_value = current_fingerprint.get(key)
        if baseline_value != current_value:
            changed_fields.append(key)
            baseline_summary[key] = baseline_value
            current_summary[key] = current_value

    if not changed_fields:
        return None

    return {
        "changed_fields": changed_fields,
        "baseline": baseline_summary,
        "current": current_summary,
    }


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _build_untracked_review_artifact(repo_root: Path, untracked_paths: list[str], *args: str) -> str:
    if not untracked_paths:
        return ""
    outputs: list[str] = []
    for rel_path in untracked_paths:
        output = _git_output_with_returncodes(
            repo_root,
            "diff",
            "--no-index",
            "--no-ext-diff",
            *args,
            "--",
            os.devnull,
            rel_path,
            allowed_returncodes=(0, 1),
        )
        if output:
            outputs.append(output)
    return "".join(outputs)


def _combine_artifact_output(*parts: str) -> str:
    combined: list[str] = []
    for part in parts:
        if not part:
            continue
        if combined and not combined[-1].endswith("\n") and not part.startswith("\n"):
            combined.append("\n")
        combined.append(part)
    return "".join(combined)


def _summarize_status(status_output: str) -> dict[str, object]:
    affected_paths: list[str] = []
    tracked_change_count = 0
    untracked_count = 0

    for raw_line in status_output.splitlines():
        if not raw_line:
            continue
        if raw_line.startswith("?? "):
            untracked_count += 1
        else:
            tracked_change_count += 1
        path_text = raw_line[3:]
        if " -> " in path_text:
            _, path_text = path_text.split(" -> ", 1)
        normalized_path = path_text.strip()
        if normalized_path and normalized_path not in affected_paths:
            affected_paths.append(normalized_path)

    return {
        "is_dirty": bool(affected_paths),
        "tracked_change_count": tracked_change_count,
        "untracked_count": untracked_count,
        "affected_paths": affected_paths,
    }
