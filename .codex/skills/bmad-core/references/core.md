# BMAD Core Notes (from docs)

## Install
- Run `npx bmad-method install` (Node.js 20+ required).
- Choose install location, AI tools, and modules during the installer prompts.

## Repo Layout
- `_bmad/` contains core + selected modules and per-module `config.yaml`.
- `_bmad-output/` contains generated artifacts (PRD, architecture, stories, etc.).
- Tool-specific command files may be created (e.g., `.claude/`).

## Help + Next Step
- Use `/bmad-help` (or the tool's help workflow) as the primary entry point.
- `/bmad-help` is interactive and adapts to installed modules, tracks, and project state.

## Track Selection
- BMAD auto-suggests a planning track (Quick Flow, BMad Method, or Enterprise) based on complexity.
- Users can override the suggested track if needed.
