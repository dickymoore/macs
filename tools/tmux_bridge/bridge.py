#!/usr/bin/env python3
"""
MACS Bridge - Multi Agent Control System

Monitors a worker tmux pane for controller requests and routes responses.
Supports manual, auto, and interactive modes.
"""
import argparse
import hashlib
import os
import re
import shlex
import subprocess
import sys
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl

# Request/response delimiters
START_RE = re.compile(r"<<CONTROLLER_REQUEST.*>>")
END_RE = re.compile(r"<<CONTROLLER_REQUEST_END>>")
RESPONSE_START_RE = re.compile(r"<<CONTROLLER_RESPONSE.*>>")
RESPONSE_END_RE = re.compile(r"<<CONTROLLER_RESPONSE_END>>")

# Heuristic triggers for questions/completion
QUESTION_RE = re.compile(r"[A-Za-z].*\?$")
ASK_RE = re.compile(
    r"\b(what would you like|do you want|should i|shall i|"
    r"would you like|anything else|any other|question|"
    r"ready for next steps|ready to proceed)\b",
    re.IGNORECASE,
)
DONE_RE = re.compile(
    r"\b(done|complete|completed|all set|finished|ready for review|"
    r"ready to merge|ready for merge|awaiting your response)\b",
    re.IGNORECASE,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
OUTBOX_DIR = os.path.join(BASE_DIR, "outbox")
ARCHIVE_DIR = os.path.join(BASE_DIR, "archive")
DEFAULT_SYSTEM_PROMPT = os.path.join(BASE_DIR, "controller_prompt.txt")
SEND_LOCK_PATH = "/tmp/macs-bridge-send.lock"


def ensure_dirs():
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(OUTBOX_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)


def run_tmux(args, capture=False, check=True):
    result = subprocess.run(
        ["tmux"] + args,
        check=check,
        capture_output=capture,
        text=True,
    )
    return result.stdout if capture else ""


def run_tmux_input(args, input_text, check=True):
    subprocess.run(
        ["tmux"] + args,
        check=check,
        input=input_text,
        text=True,
    )


@contextmanager
def send_lock(path):
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def get_current_session():
    try:
        return run_tmux(["display-message", "-p", "#S"], capture=True).strip()
    except subprocess.CalledProcessError:
        return ""


def list_panes(session):
    fmt = "#{pane_id}\t#{window_name}\t#{pane_title}\t#{pane_current_command}\t#{pane_pid}"
    try:
        if session:
            out = run_tmux(["list-panes", "-t", session, "-F", fmt], capture=True)
        else:
            out = run_tmux(["list-panes", "-a", "-F", fmt], capture=True)
    except subprocess.CalledProcessError:
        return []
    panes = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) != 5:
            continue
        pane_id, window_name, pane_title, current_cmd, pid = parts
        panes.append({
            "pane_id": pane_id,
            "window_name": window_name,
            "pane_title": pane_title,
            "current_cmd": current_cmd,
            "pid": pid,
        })
    return panes


def pane_matches_label(pane, label):
    label = label.lower()
    return (
        label in pane["window_name"].lower()
        or label in pane["pane_title"].lower()
        or label in pane["current_cmd"].lower()
    )


def process_command_from_pid(pid):
    try:
        out = subprocess.run(
            ["ps", "-o", "command=", "-p", str(pid)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        return ""
    return out


def discover_worker_pane(session):
    """Find the worker pane by label or codex process."""
    panes = list_panes(session)
    for pane in panes:
        if pane_matches_label(pane, "worker"):
            return pane["pane_id"]
    for pane in panes:
        if "codex" in pane["current_cmd"].lower():
            return pane["pane_id"]
    for pane in panes:
        cmd = process_command_from_pid(pane["pid"])
        if "codex" in cmd.lower():
            return pane["pane_id"]
    return None


def discover_controller_pane(session, worker_pane_id=None):
    """Find the controller pane, excluding the worker pane."""
    panes = list_panes(session)
    for pane in panes:
        if pane_matches_label(pane, "controller"):
            if worker_pane_id and pane["pane_id"] == worker_pane_id:
                continue
            return pane["pane_id"]
    codex_panes = [p for p in panes if "codex" in p["current_cmd"].lower()]
    for pane in codex_panes:
        if worker_pane_id and pane["pane_id"] == worker_pane_id:
            continue
        return pane["pane_id"]
    for pane in panes:
        if worker_pane_id and pane["pane_id"] == worker_pane_id:
            continue
        cmd = process_command_from_pid(pane["pid"])
        if "codex" in cmd.lower():
            return pane["pane_id"]
    return None


def setup_pipe(pane_id, log_path):
    log_path = os.path.abspath(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    cmd = f"cat >> {shlex.quote(log_path)}"
    run_tmux(["pipe-pane", "-o", "-t", pane_id, cmd])


def stable_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def send_line(pane_id, line):
    if len(line) <= 1000:
        run_tmux(["send-keys", "-t", pane_id, "--", line, "Enter"], check=True)
        return
    buf_name = f"macs-bridge-{os.getpid()}"
    run_tmux_input(["load-buffer", "-b", buf_name, "-"], line, check=True)
    run_tmux(["paste-buffer", "-t", pane_id, "-b", buf_name], check=True)
    run_tmux(["delete-buffer", "-b", buf_name], check=False)
    run_tmux(["send-keys", "-t", pane_id, "Enter"], check=True)


def load_seen_hashes():
    seen = set()
    if not os.path.isdir(ARCHIVE_DIR):
        return seen
    for name in os.listdir(ARCHIVE_DIR):
        if not name.endswith(".request.txt"):
            continue
        path = os.path.join(ARCHIVE_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError:
            continue
        seen.add(stable_id(content))
    return seen


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def load_system_prompt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def extract_response_from_text(text):
    lines = text.splitlines()
    in_block = False
    collected = []
    for line in lines:
        if not in_block:
            if RESPONSE_START_RE.search(line):
                in_block = True
            continue
        if RESPONSE_END_RE.search(line):
            break
        collected.append(line)
    if collected:
        return "\n".join(collected).strip()
    return text.strip()


def normalize_header(line):
    normalized = line.strip().lower()
    normalized = re.sub(r"^[\s\-\*\d\.)]+\s*", "", normalized)
    return normalized


def parse_section_header(line):
    header = normalize_header(line)
    for section in ("worker instructions", "notes"):
        if header.startswith(section):
            remainder = ""
            if ":" in line:
                remainder = line.split(":", 1)[1].strip()
            return section.split()[0], remainder
    return None, ""


def split_worker_and_notes(text):
    worker_lines = []
    notes_lines = []
    section = None

    for line in text.splitlines():
        parsed_section, remainder = parse_section_header(line)
        if parsed_section:
            section = parsed_section
            if remainder:
                if section == "worker":
                    worker_lines.append(remainder)
                else:
                    notes_lines.append(remainder)
            continue
        if section == "worker":
            worker_lines.append(line)
        elif section == "notes":
            notes_lines.append(line)
    worker_text = "\n".join(worker_lines).strip()
    notes_text = "\n".join(notes_lines).strip()
    return worker_text, notes_text


def read_recent_worker_context(log_path, max_lines):
    if not log_path or max_lines <= 0:
        return ""
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
    except OSError:
        return ""
    if not lines:
        return ""
    tail = lines[-max_lines:]
    cleaned = []
    in_block = False
    for line in tail:
        if START_RE.search(line):
            in_block = True
            continue
        if in_block:
            if END_RE.search(line):
                in_block = False
            continue
        cleaned.append(line)
    context = "\n".join(cleaned).strip()
    return context


def run_codex_controller(block_text, args):
    system_prompt = load_system_prompt(args.controller_system_prompt)
    prompt_parts = []
    if system_prompt:
        prompt_parts.append(system_prompt)
    prompt_parts.append("Controller request:")
    prompt_parts.append(block_text.strip())
    prompt_parts.append(
        "Respond with a controller response wrapped in these delimiters:\n"
        "<<CONTROLLER_RESPONSE>>\n"
        "WORKER INSTRUCTIONS:\n"
        "...instructions...\n"
        "NOTES:\n"
        "...notes...\n"
        "<<CONTROLLER_RESPONSE_END>>"
    )
    prompt = "\n\n".join(prompt_parts)

    cmd = ["codex", "exec", "--skip-git-repo-check", prompt, "--sandbox", "read-only"]
    if args.controller_model:
        cmd.extend(["--model", args.controller_model])
    if args.controller_extra_args:
        cmd.extend(shlex.split(args.controller_extra_args))

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()
    if not output:
        output = result.stderr.strip()
    return extract_response_from_text(output)


def wait_for_controller_response(log_path, req_id=None, timeout=300):
    start_time = time.time()
    last_activity = time.time()
    buffer = ""
    in_block = False
    collected = []
    start_id = None
    collecting = False
    seen_worker = False
    seen_notes = False

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        while True:
            if timeout and time.time() - start_time > timeout:
                return ""
            chunk = f.read(4096)
            if not chunk:
                if collecting and seen_notes and time.time() - last_activity > 1.0:
                    return "\n".join(collected).strip()
                time.sleep(0.2)
                continue
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                last_activity = time.time()
                if not in_block:
                    if RESPONSE_START_RE.search(line):
                        in_block = True
                        collected = []
                        start_id = None
                        m = re.search(r"id=([^\s>]+)", line)
                        if m:
                            start_id = m.group(1)
                        continue
                    header = normalize_header(line)
                    if header.startswith("worker instructions"):
                        collecting = True
                        seen_worker = True
                        collected = [line]
                        continue
                    if collecting:
                        collected.append(line)
                        if header.startswith("notes"):
                            seen_notes = True
                    continue
                if RESPONSE_END_RE.search(line):
                    if req_id and start_id and start_id != req_id:
                        in_block = False
                        collected = []
                        start_id = None
                        continue
                    return "\n".join(collected).strip()
                collected.append(line)
                header = normalize_header(line)
                if header.startswith("notes"):
                    seen_notes = True


def run_codex_interactive(block_text, args, controller_pane_id, req_id):
    lines = [args.controller_command]
    lines.append(f"<<CONTROLLER_REQUEST id={req_id}>>")
    lines.extend(block_text.strip().split("\n"))
    lines.append("<<CONTROLLER_REQUEST_END>>")
    with send_lock(SEND_LOCK_PATH):
        for line in lines:
            send_line(controller_pane_id, line)
    return wait_for_controller_response(
        args.controller_log, req_id=req_id, timeout=args.controller_timeout
    )


def generate_auto_response(block_text):
    return """WORKER INSTRUCTIONS:
AUTO MODE PLACEHOLDER
- Continue with the safest approach.
- Maintain all security invariants.
- Report back when complete or blocked.

Requested block:
{block}

NOTES:
Auto response generated (no controller backend configured).
""".format(block=block_text.strip())


def generate_empty_controller_response(block_text):
    return """WORKER INSTRUCTIONS:
Controller backend did not return a response (timeout or error).
Please resend the last request and include any critical context or logs.

NOTES:
Controller backend returned an empty response. Check controller session/logs and retry.
"""


def send_response(pane_id, response_text):
    for line in response_text.split("\n"):
        send_line(pane_id, line)


def wait_for_response(path):
    while True:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        time.sleep(0.5)


def handle_block(block_text, args, pane_id, seen_hashes, simulate=False, controller_pane_id=None):
    block_hash = stable_id(block_text)
    if block_hash in seen_hashes:
        return
    seen_hashes.add(block_hash)

    req_id = f"{timestamp()}_{block_hash}"
    inbox_path = os.path.join(INBOX_DIR, f"{req_id}.request.txt")
    archive_req = os.path.join(ARCHIVE_DIR, f"{req_id}.request.txt")
    write_file(inbox_path, block_text)
    write_file(archive_req, block_text)

    if simulate:
        print(f"[simulate] wrote {inbox_path}")
        return

    if args.mode == "manual":
        response_path = os.path.join(OUTBOX_DIR, f"{req_id}.response.txt")
        print(f"Controller request captured: {inbox_path}")
        print(f"Write response to: {response_path}")
        response_text = wait_for_response(response_path)
    else:
        controller_block = block_text
        if args.worker_context_lines > 0:
            context = read_recent_worker_context(args.log, args.worker_context_lines)
            if context:
                controller_block = (
                    f"{block_text.strip()}\n\n[WORKER_CONTEXT]\n{context}\n"
                )
        if args.controller_backend == "codex-interactive":
            if not controller_pane_id:
                print("Controller pane not configured for interactive backend.")
                return
            response_text = run_codex_interactive(
                controller_block, args, controller_pane_id, req_id
            )
        elif args.controller_backend == "codex":
            response_text = run_codex_controller(controller_block, args)
        else:
            response_text = generate_auto_response(controller_block)
        if not response_text.strip():
            print("[bridge] warning: Controller backend returned empty response; sending retry guidance.")
            response_text = generate_empty_controller_response(controller_block)
        response_path = os.path.join(OUTBOX_DIR, f"{req_id}.response.txt")
        write_file(response_path, response_text)

    archive_resp = os.path.join(ARCHIVE_DIR, f"{req_id}.response.txt")
    write_file(archive_resp, response_text)

    if args.split_response:
        worker_text, notes_text = split_worker_and_notes(response_text)
        if worker_text:
            response_text = worker_text
        else:
            print("[bridge] warning: could not find WORKER INSTRUCTIONS section; sending full response.")
        if notes_text:
            print("[notes]")
            print(notes_text)

    if args.dry_run:
        print("[dry-run] would send response:")
        print(response_text)
        return

    print(f"[bridge] sending to worker pane {pane_id} ({len(response_text.splitlines())} lines)")
    send_response(pane_id, response_text)


def is_heuristic_trigger(line):
    if ASK_RE.search(line):
        return True
    if DONE_RE.search(line):
        return True
    if "?" in line and QUESTION_RE.search(line):
        return True
    return False


def build_heuristic_block(lines):
    return "\n".join(["<<CONTROLLER_REQUEST heuristic>>"] + lines + ["<<CONTROLLER_REQUEST_END>>"])


def parse_stream(stream, on_block, heuristic_enabled=False, heuristic_lines=20):
    in_block = False
    block_lines = []
    buffer = ""
    recent_lines = deque(maxlen=heuristic_lines)

    def handle_line(line):
        nonlocal in_block, block_lines
        if line is not None:
            recent_lines.append(line)
        if not in_block:
            if START_RE.search(line):
                in_block = True
                block_lines = [line]
                if END_RE.search(line):
                    on_block("\n".join(block_lines))
                    in_block = False
                    block_lines = []
                return
            if heuristic_enabled and is_heuristic_trigger(line):
                on_block(build_heuristic_block(list(recent_lines)))
            return
        block_lines.append(line)
        if END_RE.search(line):
            on_block("\n".join(block_lines))
            in_block = False
            block_lines = []

    while True:
        chunk = stream.read(4096)
        if not chunk:
            time.sleep(0.2)
            continue
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            handle_line(line)


def parse_file(path, on_block, heuristic_enabled=False, heuristic_lines=20):
    with open(path, "r", encoding="utf-8") as f:
        in_block = False
        block_lines = []
        recent_lines = deque(maxlen=heuristic_lines)
        for line in f:
            line = line.rstrip("\n")
            recent_lines.append(line)
            if not in_block:
                if START_RE.search(line):
                    in_block = True
                    block_lines = [line]
                    if END_RE.search(line):
                        on_block("\n".join(block_lines))
                        in_block = False
                        block_lines = []
                    continue
                if heuristic_enabled and is_heuristic_trigger(line):
                    on_block(build_heuristic_block(list(recent_lines)))
                continue
            block_lines.append(line)
            if END_RE.search(line):
                on_block("\n".join(block_lines))
                in_block = False
                block_lines = []


def main():
    parser = argparse.ArgumentParser(description="MACS Bridge - Multi Agent Control System")
    parser.add_argument("--session", default=None, help="tmux session name")
    parser.add_argument("--worker-pane", default=None, help="tmux pane id (e.g. %%3)")
    parser.add_argument("--log", default="/tmp/macs-worker.log", help="log path")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--simulate-log", default=None, help="parse static log file")
    parser.add_argument(
        "--controller-backend",
        choices=["none", "codex", "codex-interactive"],
        default="codex-interactive",
        help="LLM backend for auto responses",
    )
    parser.add_argument(
        "--controller-system-prompt",
        default=DEFAULT_SYSTEM_PROMPT,
        help="system prompt file for controller LLM",
    )
    parser.add_argument("--controller-model", default=None, help="model name for codex backend")
    parser.add_argument(
        "--controller-extra-args",
        default=None,
        help="extra args to pass to codex exec",
    )
    parser.add_argument("--controller-pane", default=None, help="tmux pane id for controller codex")
    parser.add_argument(
        "--controller-log", default="/tmp/macs-controller.log", help="log path for controller pane"
    )
    parser.add_argument(
        "--controller-command",
        default="/prompts:controller",
        help="slash command to invoke in controller codex",
    )
    parser.add_argument(
        "--controller-timeout",
        type=int,
        default=300,
        help="seconds to wait for controller response",
    )
    parser.add_argument(
        "--split-response",
        action="store_true",
        default=True,
        help="send only WORKER INSTRUCTIONS to worker; print NOTES locally",
    )
    parser.add_argument(
        "--no-split-response",
        action="store_false",
        dest="split_response",
        help="disable split-response behavior",
    )
    parser.add_argument(
        "--worker-context-lines",
        type=int,
        default=40,
        help="number of recent worker log lines to include for controller context",
    )
    parser.add_argument(
        "--heuristic",
        action="store_true",
        default=True,
        help="enable heuristic triggers for questions/completion",
    )
    parser.add_argument(
        "--no-heuristic",
        action="store_false",
        dest="heuristic",
        help="disable heuristic triggers",
    )
    parser.add_argument(
        "--heuristic-lines",
        type=int,
        default=20,
        help="max recent lines to include in heuristic request block",
    )
    args = parser.parse_args()

    ensure_dirs()

    if args.simulate_log:
        seen_hashes = load_seen_hashes()
        print(f"[simulate] parsing {args.simulate_log}")
        parse_file(
            args.simulate_log,
            lambda block: handle_block(block, args, None, seen_hashes, simulate=True),
            heuristic_enabled=args.heuristic,
            heuristic_lines=args.heuristic_lines,
        )
        return

    session = args.session or get_current_session()
    if not args.worker_pane and session:
        try:
            run_tmux(["has-session", "-t", session], capture=False, check=True)
        except subprocess.CalledProcessError:
            print(
                f"tmux session not found: {session}. Start controller/worker sessions first "
                "or pass --worker-pane/--controller-pane."
            )
            sys.exit(1)
    pane_id = args.worker_pane or discover_worker_pane(session)
    if not pane_id:
        print("Unable to find worker pane. Provide --worker-pane.")
        sys.exit(1)

    setup_pipe(pane_id, args.log)
    controller_pane_id = None
    if args.controller_backend == "codex-interactive":
        controller_pane_id = args.controller_pane or discover_controller_pane(session, worker_pane_id=pane_id)
        if not controller_pane_id:
            print("Unable to find controller pane. Provide --controller-pane.")
            sys.exit(1)
        setup_pipe(controller_pane_id, args.controller_log)
        controller_log_path = os.path.abspath(args.controller_log)
        if not os.path.exists(controller_log_path):
            write_file(controller_log_path, "")
    session_label = session or "all-sessions"
    print(
        f"[bridge] session={session_label} pane={pane_id} log={os.path.abspath(args.log)}"
    )
    mode_label = "auto" if args.mode == "auto" else "manual"
    heuristic_label = "on" if args.heuristic else "off"
    print(
        f"[bridge] mode={mode_label} heuristic={heuristic_label} "
        f"lines={args.heuristic_lines} controller_backend={args.controller_backend}"
    )
    if controller_pane_id:
        print(f"[bridge] controller_pane={controller_pane_id} controller_log={os.path.abspath(args.controller_log)}")

    seen_hashes = load_seen_hashes()
    log_path = os.path.abspath(args.log)
    if not os.path.exists(log_path):
        write_file(log_path, "")
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_END)
        parse_stream(
            f,
            lambda block: handle_block(
                block,
                args,
                pane_id,
                seen_hashes,
                simulate=False,
                controller_pane_id=controller_pane_id,
            ),
            heuristic_enabled=args.heuristic,
            heuristic_lines=args.heuristic_lines,
        )


if __name__ == "__main__":
    main()
