# MACS Documentation

MACS is a controller-first orchestration system for tmux-backed AI workers. This docs surface is organized by what you are trying to do: get a repo running, operate work safely, understand the control plane, or contribute to the system itself.

## Choose Your Path

### I want to use MACS in a repo

1. Read [Getting Started](./getting-started.md).
2. Keep [Using MACS](./user-guide.md) open while you work.
3. Use [How-To Recipes](./how-tos.md) for common operator flows.
4. Read [Architecture](./architecture.md) when you need the model behind the commands.

### I want to extend or contribute to MACS

1. Read [Contributor Guide](./contributor-guide.md).
2. Read [Architecture](./architecture.md) for the controller-owned model.
3. Read [Customization](./customization.md) for repo-local policy and prompt adjustments.
4. Read [Adapter Contributor Guide](./adapter-contributor-guide.md) if you are touching runtime adapters.

## Documentation Map

| Document | Audience | Purpose |
| --- | --- | --- |
| [README](../README.md) | Everyone | Project overview, quick start, and top-level validation commands |
| [Getting Started](./getting-started.md) | New operators | Bootstrap a repo-local orchestration session |
| [Using MACS](./user-guide.md) | Daily operators | Command families, core entities, and common usage examples |
| [How-To Recipes](./how-tos.md) | Operators | Task-focused procedures for setup, intervention, recovery, and release readiness |
| [Architecture](./architecture.md) | Operators and contributors | Controller-first mental model plus Mermaid diagrams |
| [Customization](./customization.md) | Maintainers | Repo-local config, prompts, bridge options, and environment tuning |
| [Contributor Guide](./contributor-guide.md) | Contributors | Repo map, development workflow, testing, and docs maintenance rules |
| [Adapter Contributor Guide](./adapter-contributor-guide.md) | Adapter contributors | Shared adapter contract, qualification workflow, and anti-patterns |

## What Is Canonical

- The live CLI help surface is authoritative for flags and command families.
- Controller state is authoritative for `worker`, `task`, `lease`, `lock`, and `event`.
- Planning artifacts under `_bmad-output/planning-artifacts/` explain intent, but docs in this folder should describe implemented behavior.
- Release evidence under `_bmad-output/release-evidence/` is the Phase 1 proof package for this repository state.

## Reading Order by Topic

### Bootstrap and onboarding

- [Getting Started](./getting-started.md)
- [How-To Recipes](./how-tos.md#bootstrap-a-repo-local-control-plane)
- [Customization](./customization.md)

### Daily operations

- [Using MACS](./user-guide.md)
- [How-To Recipes](./how-tos.md#assign-work-with-routing-policy)
- [How-To Recipes](./how-tos.md#pause-inspect-and-resume-a-task)

### Recovery and audit

- [Using MACS](./user-guide.md#inspect-and-recover-controller-owned-state)
- [How-To Recipes](./how-tos.md#inspect-and-resolve-recovery)
- [Architecture](./architecture.md#intervention-and-recovery-flow)

### Contributing code

- [Contributor Guide](./contributor-guide.md)
- [Adapter Contributor Guide](./adapter-contributor-guide.md)
- [Architecture](./architecture.md)
