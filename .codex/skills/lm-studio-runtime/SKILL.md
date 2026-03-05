---
name: lm-studio-runtime
description: "LM Studio runtime/session control: use lms CLI commands to manage models and servers in a worker terminal. Trigger when the controller needs to operate LM Studio CLI like a human."
---

# LM Studio Runtime

## Overview
Operate the LM Studio CLI safely: download models, load/unload them, and manage the local inference server.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

## Core Commands (LM Studio CLI)

Common commands:
- `lms ls` list available models.
- `lms get <model>` download a model.
- `lms load <model>` load a model for inference.
- `lms unload <model>` unload a model.
- `lms ps` show running models.
- `lms server start` start the local server.
- `lms server stop` stop the local server.
- `lms server status` show server status.
- `lms log stream` stream server logs.
- `lms runtime` show runtime information.

## Guardrails

- Do not restart mid-run.
- Use `lms server stop` before restarting the server.
- If the worker is not LM Studio CLI, switch to the model-specific runtime skill instead.
