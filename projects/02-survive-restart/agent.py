"""Project 2: survive a restart.

Run once to start a task, hard-kill it mid-run with:
    taskkill /F /PID <pid>
then run again with the same task/progress-file path to resume.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01-bare-metal-loop"))
from tools import DISPATCH, TOOLS_SCHEMA  # noqa: E402

from state import Progress, load, save_atomic  # noqa: E402

MODEL = "qwen3.5:4b"
MAX_TURNS = 25
MAX_JSON_RETRIES = 2
PROGRESS_PATH = Path(__file__).parent / "progress.json"

DEFAULT_TASK = "create 3 files, then a 4th that summarizes the first 3"
# Hardcoded rather than model-generated: this project is testing whether
# resume-from-disk works, not whether the 4B can plan. One tool call is
# expected to satisfy each step (see the "one tool call == one step"
# simplification in run(), below).
DEFAULT_PLAN = [
    "create file1.txt with a short one-line placeholder sentence",
    "create file2.txt with a short one-line placeholder sentence",
    "create file3.txt with a short one-line placeholder sentence",
    "read file1.txt, file2.txt, and file3.txt, then write a summary of "
    "their contents to summary.txt",
]

SYSTEM_PROMPT = (
    "You are a careful local coding agent working through a multi-step "
    "task one step at a time. Each time you are invoked you are a fresh "
    "process with no memory of earlier turns beyond the summary you're "
    "given below -- if you need the exact contents of something from an "
    "earlier step (e.g. a file you created), use read_file to check it "
    "rather than guessing or trusting your memory of writing it. "
    "Use the available tools to complete the CURRENT STEP only, then "
    'stop. If you cannot produce a structured tool call, reply with '
    'exactly one JSON object of the form {"name": "<tool>", "arguments": '
    '{...}} and nothing else.'
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


def seed_plan(task: str) -> list[str]:
    if task == DEFAULT_TASK:
        return list(DEFAULT_PLAN)
    return [task]  # single-step fallback for an arbitrary task


def build_messages(progress: Progress, current_step: str) -> list[dict]:
    """Reconstruct the conversation from the structured summary, not a
    replayed transcript. This is the thing Project 2 is actually testing --
    see measurements/results.md for the comparison against naive replay.
    """
    completed = "\n".join(f"- {s}" for s in progress.steps_completed) or "(none yet)"
    note = (
        f"Overall task: {progress.task}\n\n"
        f"Steps completed so far:\n{completed}\n\n"
        f"Result of the most recent tool call:\n"
        f"{progress.last_tool_result or '(none yet)'}\n\n"
        f"CURRENT STEP -- do this now: {current_step}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": note},
    ]


def run(task: str) -> bool:
    progress = load(PROGRESS_PATH)
    if progress is None:
        progress = Progress(task=task, steps_remaining=seed_plan(task))
        save_atomic(PROGRESS_PATH, progress)
        print(f"Starting fresh: {len(progress.steps_remaining)} step(s) planned", flush=True)
    else:
        print(
            f"Resuming: {len(progress.steps_completed)} step(s) already done, "
            f"{len(progress.steps_remaining)} remaining",
            flush=True,
        )

    log_path = Path(__file__).parent / "measurements" / "tokens.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    json_retries = 0
    for turn in range(MAX_TURNS):
        if not progress.steps_remaining:
            print("[done] all planned steps complete", flush=True)
            return True

        current_step = progress.steps_remaining[0]
        print(f"[turn {turn}] working on: {current_step}", flush=True)

        messages = build_messages(progress, current_step)
        result = chat(MODEL, messages, tools=TOOLS_SCHEMA)
        log_token_usage(log_path, turn, result)
        print(
            f"[turn {turn}] {result.prompt_tokens} prompt / "
            f"{result.completion_tokens} completion tokens",
            flush=True,
        )

        tool_calls = _normalize_tool_calls(result.message)

        if tool_calls is None:
            # Anthropic's harness posts are explicit that a model's own
            # "I'm done" claim isn't trustworthy on its own (Project 4
            # builds a real evaluator for this) -- here, the cheap version
            # of that skepticism is: steps_remaining is the source of
            # truth, not the model's message, so a plain-text reply while
            # steps remain is treated as a non-answer and retried.
            print(
                f"[turn {turn}] model replied with plain text while "
                f"{len(progress.steps_remaining)} step(s) remain -- retrying",
                flush=True,
            )
            continue

        if not tool_calls:
            json_retries += 1
            print(
                f"[turn {turn}] malformed tool-call JSON "
                f"(retry {json_retries}/{MAX_JSON_RETRIES})",
                flush=True,
            )
            if json_retries > MAX_JSON_RETRIES:
                return False
            continue

        step_output = None
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
            preview = str(output)[:200] + ("..." if len(str(output)) > 200 else "")
            print(f"[turn {turn}] {name} -> {preview}", flush=True)
            step_output = output

        # Simplifying assumption for this project: one turn's worth of
        # tool calls satisfies one planned step. Update state in memory,
        # then hit disk BEFORE the next chat() call is made -- if the
        # process dies between here and the next turn, the resumed run
        # sees this step as done and doesn't repeat it.
        progress.steps_completed.append(current_step)
        progress.steps_remaining.pop(0)
        progress.last_tool_result = str(step_output)
        save_atomic(PROGRESS_PATH, progress)

    return False  # hit MAX_TURNS without finishing every planned step


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or DEFAULT_TASK
    success = run(task)
    print("SUCCESS" if success else "FAILED (max turns)")
