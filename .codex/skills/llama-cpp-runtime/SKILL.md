---
name: llama-cpp-runtime
description: "llama.cpp runtime/session control: use llama-cli and llama-server commands/flags to run local GGUF models and serve an API in a worker terminal. Trigger when the controller needs to operate llama.cpp like a human."
---

# llama.cpp Runtime

## Overview
Operate llama.cpp safely: run local GGUF models via `llama-cli` or serve an API via `llama-server`.

## Session Safety

1) Confirm idle state
- Snapshot and/or `status` the worker; do not intervene mid-run.
- Only proceed when the worker is at a prompt or explicitly idle.

## Core Commands

### `llama-cli` (interactive/local runs)
- Run a local model file:
  - `llama-cli -m my_model.gguf`
- Download and run directly from Hugging Face:
  - `llama-cli -hf ggml-org/gemma-3-1b-it-GGUF`
- Conversation mode (if not auto-enabled):
  - `llama-cli -m model.gguf -cnv --chat-template chatml`

### `llama-server` (OpenAI-compatible API)
- Start a local server on port 8080:
  - `llama-server -m model.gguf --port 8080`
- Parallel decoding example:
  - `llama-server -m model.gguf -c 16384 -np 4`

## Guardrails

- Do not restart mid-run.
- Use `llama-server` for API-style usage and `llama-cli` for interactive/local prompts.
- If the worker is not llama.cpp, switch to the model-specific runtime skill instead.
