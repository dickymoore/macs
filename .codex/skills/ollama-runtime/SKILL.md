---
name: ollama-runtime
description: "Ollama runtime/session control: use ollama CLI commands to run models, manage downloads, and stop running models in a worker terminal. Trigger when the controller needs to operate Ollama like a human."
---

# Ollama Runtime

## Overview
Operate the Ollama CLI safely: run models, manage downloads, and stop running sessions from a worker terminal.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

2) Prefer shell-level control
- Ollama does not use slash commands; manage sessions via `ollama` subcommands.

## Core Commands (Ollama CLI)

Common commands:
- `ollama run <model>` run a model (interactive chat if no prompt is supplied).
- `ollama pull <model>` download a model.
- `ollama list` list local models.
- `ollama ps` list running models.
- `ollama stop <model>` stop a running model.
- `ollama show <model>` show model information.
- `ollama create <model>` create a model from a Modelfile.
- `ollama rm <model>` remove a model.
- `ollama cp <source> <dest>` copy a model.
- `ollama serve` start the server.
- `ollama help` show help.

## Guardrails

- Do not restart mid-run; use `ollama stop` to end a running model session.
- If the worker is not Ollama, switch to the model-specific runtime skill instead.
