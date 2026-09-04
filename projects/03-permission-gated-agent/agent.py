"""Project 3: permission-gated file agent.

Task: organize/rename files in a real messy folder, staying inside
`WORKSPACE_ROOT`. Every tool call goes through policy.Allowlist.check()
and audit.record() before it executes.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

from audit import record  # noqa: E402
from policy import Allowlist, PolicyViolation  # noqa: E402
from tools import DISPATCH, TOOL_ACTIONS, TOOLS_SCHEMA  # noqa: E402

MODEL = os.environ.get("HARNESS_MODEL", "qwen3.5:4b")
MAX_TURNS = 20
MAX_JSON_RETRIES = 2
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", str(Path(__file__).parent / "sandbox"))
AUDIT_LOG = Path(__file__).parent / "measurements" / "audit.jsonl"

allowlist = Allowlist([WORKSPACE_ROOT])

SYSTEM_PROMPT = (
    "You are a careful local file-organizing agent. You may only read, "
    "write, list, move, or delete files inside {root} -- nothing outside "
    "that directory exists as far as you're concerned, and attempts to "
    "reach outside it will be refused and logged, not silently allowed. "
    "Deleting a file or overwriting an existing one may require a "
    "confirmation this harness controls, not you -- if a tool call comes "
    "back with an error, do not retry the same path, explain what "
    "happened instead. Use the available tools to complete the task. If "
    "you cannot produce a structured tool call, reply with exactly one "
    'JSON object of the form {{"name": "<tool>", "arguments": {{...}}}} '
    "and nothing else."
)


def _confirm(action: str, path: str) -> bool:
    """Manual confirmation gate for destructive actions.

    A container run has no interactive TTY, so this fails CLOSED (refuses)
    rather than blocking forever on input() when stdin isn't a terminal --
    an agent that can't get confirmation shouldn't proceed by default.
    """
    if not sys.stdin.isatty():
        print(
            f"[confirm] {action} on {path} needs interactive confirmation; "
            "none available (non-tty) -- refusing",
            flush=True,
        )
        return False
    reply = input(f"Allow {action} on {path}? [y/N] ").strip().lower()
    return reply == "y"


def gated_call(tool_name: str, args: dict, fn):
    action, path_keys = TOOL_ACTIONS[tool_name]
    audit_target = ", ".join(str(args[k]) for k in path_keys)

    resolved = {}
    try:
        for key in path_keys:
            resolved[key] = allowlist.check(args[key])
    except PolicyViolation as e:
        record(AUDIT_LOG, action, audit_target, allowed=False, reason=str(e))
        raise

    if tool_name == "write_file" and resolved["path"].exists():
        action = "overwrite"

    if allowlist.requires_confirmation(action):
        if not _confirm(action, audit_target):
            record(AUDIT_LOG, action, audit_target, allowed=False, reason="not confirmed")
            raise PermissionError(f"{action} on {audit_target} was not confirmed")

    call_args = {**args, **{k: str(v) for k, v in resolved.items()}}
    result = fn(**call_args)
    record(AUDIT_LOG, action, audit_target, allowed=True)
    return result


def _looks_like_tool_call_attempt(content: str) -> bool:
    return content.strip().startswith("{")


def _try_parse_manual_tool_call(content: str) -> dict | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict) or "name" not in parsed:
        return None
    return parsed


def _normalize_tool_calls(message: dict) -> list[dict] | None:
    tool_calls = message.get("tool_calls")
    if tool_calls:
        return tool_calls

    content = message.get("content") or ""
    if not _looks_like_tool_call_attempt(content):
        return None

    parsed = _try_parse_manual_tool_call(content)
    if parsed is None:
        return []

    return [{"function": {"name": parsed.get("name"), "arguments": parsed.get("arguments", {})}}]


def run(task: str) -> bool:
    Path(WORKSPACE_ROOT).mkdir(parents=True, exist_ok=True)
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(root=WORKSPACE_ROOT)},
        {"role": "user", "content": task},
    ]
    log_path = Path(__file__).parent / "measurements" / "tokens.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    json_retries = 0
    for turn in range(MAX_TURNS):
        print(f"[turn {turn}] waiting on model...", flush=True)
        result = chat(MODEL, messages, tools=TOOLS_SCHEMA)
        log_token_usage(log_path, turn, result)

        message = result.message
        messages.append(message)
        tool_calls = _normalize_tool_calls(message)

        if tool_calls is None:
            print(f"[turn {turn}] final answer, done", flush=True)
            return True

        if not tool_calls:
            json_retries += 1
            print(
                f"[turn {turn}] malformed tool-call JSON "
                f"(retry {json_retries}/{MAX_JSON_RETRIES})",
                flush=True,
            )
            if json_retries > MAX_JSON_RETRIES:
                return False
            messages.append(
                {
                    "role": "tool",
                    "content": (
                        "Your last message wasn't valid JSON for a tool call. "
                        "Reply with either a proper tool call or a plain-text "
                        "final answer."
                    ),
                }
            )
            continue

        for call in tool_calls:
            fn_call = call["function"]
            name = fn_call["name"]
            args = fn_call.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            print(f"[turn {turn}] calling {name}({args})", flush=True)
            try:
                if name not in DISPATCH:
                    raise ValueError(f"unknown tool: {name}")
                output = gated_call(name, args, DISPATCH[name])
            except Exception as e:  # policy refusals and tool errors are fed back, not fatal
                output = f"error: {e}"
            preview = str(output)[:200] + ("..." if len(str(output)) > 200 else "")
            print(f"[turn {turn}] {name} -> {preview}", flush=True)
            messages.append({"role": "tool", "content": str(output)})

    return False  # hit MAX_TURNS without a clean finish


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "organize the files in the workspace by extension"
    success = run(task)
    print("SUCCESS" if success else "FAILED")
