# Customizing MACS

This guide covers how to adapt MACS for your specific project needs.

## Controller Prompt Customization

### Adding Project-Specific Rules

Edit `.codex/prompts/controller.md` and add your rules at the bottom:

```markdown
## Project-Specific Rules

### Repository Structure
- Source code in `src/`
- Tests in `tests/`
- Documentation in `docs/`

### CI/CD Requirements
- All PRs require passing tests
- Coverage must be >= 80%
- Linting must pass

### Security Policies
- No secrets in code
- Use environment variables for configuration
- All API endpoints require authentication

### Team Conventions
- Use conventional commits
- PRs require one approval
- Squash merge to main
```

### Customizing Decision Priorities

Reorder or modify the decision priorities section:

```markdown
## Decision Priorities (Highest to Lowest)

1. **Data Privacy** (GDPR, user consent)
2. **Security & authentication**
3. **Test coverage** (minimum 90%)
4. **Performance** (response time < 200ms)
5. **Code style consistency**
```

### Adding Domain-Specific Invariants

Add invariants specific to your domain:

```markdown
## Domain Invariants (Non-Negotiable)

### Financial
- All monetary calculations use decimal types
- Transactions are idempotent
- Audit logs are immutable

### Healthcare
- PHI is encrypted at rest and in transit
- Access is logged and auditable
- Data retention policies enforced
```

## Bridge Configuration

### Environment Variables

Create a `.env` file or export variables:

```bash
# Pane discovery
export TARGET_PANE_LABEL=worker
export TARGET_PANE_LINES=200
export TARGET_PANE_BUSY_LINES=40

# Input handling
export TARGET_PANE_SUBMIT_KEYS="Enter"
export TARGET_PANE_TYPE_DELAY_MS=400
export TARGET_PANE_GUARD_BUSY=1

# Timing
export TARGET_PANE_SUBMIT_DELAY_MS=200
export TARGET_PANE_SUBMIT_REPEAT=1
```

### Bridge Arguments

Common configurations:

```bash
# High-context mode (more worker history to controller)
./bridge.py --worker-context-lines 100

# Strict mode (no heuristics, explicit requests only)
./bridge.py --no-heuristic

# Verbose debugging
./bridge.py --dry-run --simulate-log /path/to/log

# Custom controller model
./bridge.py --controller-model gpt-4-turbo --controller-extra-args "--temperature 0.2"
```

### Custom System Prompts

Create project-specific system prompts:

```bash
cp tools/tmux_bridge/controller_prompt.txt my_project_prompt.txt
# Edit my_project_prompt.txt
./bridge.py --controller-system-prompt ./my_project_prompt.txt
```

## Multiple Worker Support

### Running Multiple Bridges

For multiple workers, run separate bridge instances:

```bash
# Terminal 1: Bridge for worker A
./bridge.py --worker-pane %3 --log /tmp/worker-a.log --controller-log /tmp/ctrl-a.log

# Terminal 2: Bridge for worker B
./bridge.py --worker-pane %5 --log /tmp/worker-b.log --controller-log /tmp/ctrl-b.log
```

### Shared Controller

Multiple bridges can route to the same controller pane, but ensure request IDs prevent conflicts.

## Custom Request/Response Protocols

### Modifying Delimiters

Edit the regex patterns in `bridge.py`:

```python
# Custom delimiters
START_RE = re.compile(r"@@@NEED_GUIDANCE@@@")
END_RE = re.compile(r"@@@END_REQUEST@@@")
```

### Adding Request Types

Extend the protocol with typed requests:

```
<<CONTROLLER_REQUEST type=security-review>>
Please review this authentication change.
<<CONTROLLER_REQUEST_END>>
```

Handle in bridge:
```python
def handle_block(block_text, args, ...):
    if "type=security-review" in block_text:
        # Use security-focused prompt
        args.controller_system_prompt = "security_prompt.txt"
```

## Integration Examples

### With CI/CD

```bash
#!/bin/bash
# ci-controller.sh - Run controller in CI

./bridge.py \
  --mode auto \
  --controller-backend codex \
  --controller-model gpt-4 \
  --no-heuristic \
  --controller-timeout 60
```

### With Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y tmux

COPY tools/tmux_bridge /app/bridge
WORKDIR /app/bridge

CMD ["python", "bridge.py", "--mode", "manual"]
```

### With Systemd

```ini
[Unit]
Description=MACS Bridge
After=network.target

[Service]
Type=simple
User=developer
WorkingDirectory=/home/developer/project
ExecStart=/home/developer/project/tools/tmux_bridge/bridge.py --session dev
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Logging and Debugging

### Enable Verbose Output

The bridge prints status messages to stdout. Redirect for logging:

```bash
./bridge.py 2>&1 | tee bridge.log
```

### Archive Analysis

Review historical requests/responses:

```bash
ls tools/tmux_bridge/archive/
cat tools/tmux_bridge/archive/20240115T143022Z_abc123.request.txt
cat tools/tmux_bridge/archive/20240115T143022Z_abc123.response.txt
```

### Simulate Mode

Test request detection without affecting terminals:

```bash
./bridge.py --simulate-log /path/to/captured.log
```

## Performance Tuning

### Reduce Latency

```bash
# Shorter polling intervals (in bridge.py)
time.sleep(0.1)  # Instead of 0.2

# Faster submit
export TARGET_PANE_TYPE_DELAY_MS=100
export TARGET_PANE_SUBMIT_DELAY_MS=50
```

### Reduce Context Size

```bash
# Less history to controller (faster, cheaper)
./bridge.py --worker-context-lines 20
```

### Batch Mode

For high-volume scenarios, process multiple requests before responding:

```python
# Custom modification in bridge.py
def handle_blocks_batch(blocks, args, ...):
    combined = "\n---\n".join(blocks)
    # Single controller call for all
```
