"""Generator role: produces a solution, self-reports done/not-done.

The self-report is deliberately trusted nowhere else in this project —
evaluator.py is the only source of truth for whether a task actually
succeeded.

Run (from this directory): uv run python -c "from generator import
generate; print(generate('write tasks/solutions/x.py with def f(): return 1'))"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

MODEL = "qwen3.5:4b"
MAX_TURNS = 10

# Deliberately minimal tool set (write_file/read_file only) — this role
# writes a solution file, it doesn't need Project 1's run_command.
SYSTEM_PROMPT = (
    "You are a careful local coding agent. Use the write_file tool to save "
    "your solution to the exact path given in the task — read_file is "
    "available if you need to check what you already wrote. When you are "
    "completely done, reply with plain text (no tool call) that starts "
    "with exactly one of TASK_COMPLETE or TASK_FAILED, followed by one "
    "short sentence explaining why."
)

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write UTF-8 text to a file, overwriting it if it exists. "
                "Creates parent directories as needed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


def _write_file(path: str, content: str) -> str:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {resolved}"


def _read_file(path: str) -> str:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} -> {resolved} does not exist")
    return resolved.read_text(encoding="utf-8")


DISPATCH = {"write_file": _write_file, "read_file": _read_file}


def _parse_self_report(content: str) -> bool:
    """TASK_COMPLETE -> True. Anything else — TASK_FAILED, an unlabelled
    final answer, silence — is treated as False. An unlabelled answer is
    deliberately not a success claim: the model has to actually say so.
    """
    return content.strip().upper().startswith("TASK_COMPLETE")


def generate(task: str, feedback: str | None = None) -> tuple[str, bool]:
    """Returns (solution_code_or_summary, self_reported_success)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    if feedback:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous attempt was rejected by the evaluator: "
                    f"{feedback}\nFix the solution file and try again."
                ),
            }
        )

    log_path = Path(__file__).parent / "measurements" / "tokens.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for turn in range(MAX_TURNS):
        result = chat(MODEL, messages, tools=TOOLS_SCHEMA)
        log_token_usage(log_path, turn, result)
        message = result.message
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            content = message.get("content") or ""
            return content, _parse_self_report(content)

        for call in tool_calls:
            fn = call["function"]
            name = fn["name"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            try:
                output = DISPATCH[name](**args)
            except Exception as e:  # tool failure is fed back, not fatal
                output = f"error: {e}"
            messages.append({"role": "tool", "content": str(output)})

    return "max turns exceeded without a final answer", False
