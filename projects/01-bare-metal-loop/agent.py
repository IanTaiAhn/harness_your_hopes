"""Project 1: bare-metal tool loop.

Run: uv run python agent.py "read this file, count the lines,
write the count to a new file"
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

from tools import DISPATCH, TOOLS_SCHEMA  # noqa: E402

MODEL = os.environ.get("HARNESS_MODEL", "qwen3.5:4b")
MAX_TURNS = 15
MAX_JSON_RETRIES = 2  # toggle this to 0 for the Project 1 "measure" ablation

SYSTEM_PROMPT = (
    "You are a careful local coding agent. Use the available tools to "
    "complete the task. If you cannot produce a structured tool call, "
    'reply with exactly one JSON object of the form {"name": "<tool>", '
    '"arguments": {...}} and nothing else. Any other reply is treated as '
    "your final answer and ends the task."
)


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
    """Returns a list of {"function": {"name", "arguments"}} dicts, or
    None if this message has no tool call (structured or recovered).
    """
    tool_calls = message.get("tool_calls")
    if tool_calls:
        return tool_calls

    content = message.get("content") or ""
    if not _looks_like_tool_call_attempt(content):
        return None

    parsed = _try_parse_manual_tool_call(content)
    if parsed is None:
        return []  # malformed attempt, caller handles the retry

    return [{"function": {"name": parsed.get("name"), "arguments": parsed.get("arguments", {})}}]


def run(task: str, diagnostics: dict | None = None) -> bool:
    """diagnostics, if given, is filled in-place with why the run ended
    the way it did (stop_reason/turns_used/json_retries/last_error) —
    optional and additive so existing callers passing just `task` are
    unaffected. This is what measure.py needs to tell "hit max turns"
    apart from "gave up on malformed JSON" instead of just a bool.
    """
    if diagnostics is None:
        diagnostics = {}
    diagnostics.setdefault("stop_reason", None)
    diagnostics.setdefault("turns_used", 0)
    diagnostics.setdefault("json_retries", 0)
    diagnostics.setdefault("last_error", None)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    log_path = Path(__file__).parent / "measurements" / "tokens.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    json_retries = 0
    for turn in range(MAX_TURNS):
        diagnostics["turns_used"] = turn + 1
        print(f"[turn {turn}] waiting on model...", flush=True)
        try:
            result = chat(MODEL, messages, tools=TOOLS_SCHEMA)
        except Exception as e:
            diagnostics["stop_reason"] = "chat_error"
            diagnostics["last_error"] = str(e)
            return False
        log_token_usage(log_path, turn, result)
        print(
            f"[turn {turn}] {result.prompt_tokens} prompt / "
            f"{result.completion_tokens} completion tokens",
            flush=True,
        )

        message = result.message
        messages.append(message)

        tool_calls = _normalize_tool_calls(message)

        if tool_calls is None:
            print(f"[turn {turn}] final answer, done", flush=True)
            diagnostics["stop_reason"] = "final_answer"
            return True  # plain-text final answer: task considered done

        if not tool_calls:
            json_retries += 1
            diagnostics["json_retries"] = json_retries
            print(
                f"[turn {turn}] malformed tool-call JSON "
                f"(retry {json_retries}/{MAX_JSON_RETRIES})",
                flush=True,
            )
            if json_retries > MAX_JSON_RETRIES:
                diagnostics["stop_reason"] = "max_json_retries_exceeded"
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
            fn = call["function"]
            name = fn["name"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            print(f"[turn {turn}] calling {name}({args})", flush=True)
            try:
                output = DISPATCH[name](**args)
            except Exception as e:  # tool failure is fed back, not fatal
                output = f"error: {e}"
                diagnostics["last_error"] = str(output)
            preview = str(output)[:200] + ("..." if len(str(output)) > 200 else "")
            print(f"[turn {turn}] {name} -> {preview}", flush=True)
            messages.append({"role": "tool", "content": str(output)})

    diagnostics["stop_reason"] = "max_turns"
    return False  # hit MAX_TURNS without a clean finish


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "read this file, count the lines, write the count to a new file"
    success = run(task)
    print("SUCCESS" if success else "FAILED (max turns)")
