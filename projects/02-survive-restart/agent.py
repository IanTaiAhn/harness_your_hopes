"""Project 2: survive a restart.

Run once to start a task, hard-kill it mid-run with:
    taskkill /F /PID <pid>
then run again with the same task/progress-file path to resume.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import ChatResult, chat, log_token_usage  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01-bare-metal-loop"))
from tools import DISPATCH, TOOLS_SCHEMA  # noqa: E402

from state import Progress, load, save_atomic  # noqa: E402

MODEL = "qwen3.5:4b"
MAX_TURNS = int(os.environ.get("HARNESS_MAX_TURNS", "25"))
MAX_JSON_RETRIES = 2
PROGRESS_PATH = Path(os.environ.get("HARNESS_PROGRESS_PATH", str(Path(__file__).parent / "progress.json")))

# measure.py's kill-point automation: a real `kill -9` can't be timed to
# land at a precise turn boundary without a race, so these stand in for
# "the process was hard-killed right here" -- os._exit() skips cleanup
# and exception handlers exactly like an external kill would, just at a
# deterministic point instead of a racy one.
_KILL_AFTER_TURN = os.environ.get("KILL_AFTER_TURN")
KILL_AFTER_TURN = int(_KILL_AFTER_TURN) if _KILL_AFTER_TURN is not None else None
KILL_BEFORE_FIRST_SAVE = os.environ.get("KILL_BEFORE_FIRST_SAVE") == "1"

# measure.py's crossover-length comparison: "structured" is the Progress-
# summary builder below (the thing this project is testing); "naive"
# replays the last HARNESS_REPLAY_KEEP_LAST raw turns verbatim instead,
# with no compaction -- the baseline it's being compared against.
REPLAY_MODE = os.environ.get("HARNESS_REPLAY_MODE", "structured")
REPLAY_KEEP_LAST = int(os.environ.get("HARNESS_REPLAY_KEEP_LAST", "6"))

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


SYNTHETIC_TASK_PREFIX = "synthetic:"


def seed_plan_of_length(n: int) -> list[str]:
    """N create-file steps + 1 final read-all-and-summarize step (n+1
    steps total) -- a parametrized version of DEFAULT_PLAN's shape, sized
    to force the crossover-length comparison in measurements/results.md.
    Each file's content is a distinct, greppable marker so completion is
    checkable by string search alone (check_synthetic_summary below),
    with no model judgment required.
    """
    steps = [
        f"create file{i}.txt with exactly this one-line content: MARKER_{i}_CONTENT"
        for i in range(1, n + 1)
    ]
    file_list = ", ".join(f"file{i}.txt" for i in range(1, n + 1))
    steps.append(
        f"read {file_list}, then write a summary to summary.txt that includes "
        "each file's exact one-line content, one per line, in the same order"
    )
    return steps


def check_synthetic_summary(summary_text: str, n: int) -> bool:
    """Ground truth for a seed_plan_of_length(n) run: every marker made
    it into summary.txt. No model call needed to judge this.
    """
    return all(f"MARKER_{i}_CONTENT" in summary_text for i in range(1, n + 1))


def seed_plan(task: str) -> list[str]:
    if task == DEFAULT_TASK:
        return list(DEFAULT_PLAN)
    if task.startswith(SYNTHETIC_TASK_PREFIX):
        return seed_plan_of_length(int(task[len(SYNTHETIC_TASK_PREFIX):]))
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


def build_messages_naive(task: str, full_history: list[dict], current_step: str) -> list[dict]:
    """The baseline this project's structured build_messages() is being
    measured against: no compaction at all, just the last
    REPLAY_KEEP_LAST raw turns replayed verbatim (task, assistant
    responses, tool outputs), whatever they happen to contain. This is
    expected to lose track once the plan is longer than what fits in
    that window -- that crossover point is the measurement.
    """
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Overall task: {task}"},
        *full_history[-REPLAY_KEEP_LAST:],
        {"role": "user", "content": f"CURRENT STEP -- do this now: {current_step}"},
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

    full_history: list[dict] = []  # only consulted in HARNESS_REPLAY_MODE=naive

    json_retries = 0
    for turn in range(MAX_TURNS):
        if not progress.steps_remaining:
            print("[done] all planned steps complete", flush=True)
            return True

        current_step = progress.steps_remaining[0]
        print(f"[turn {turn}] working on: {current_step}", flush=True)

        if REPLAY_MODE == "naive":
            messages = build_messages_naive(progress.task, full_history, current_step)
        else:
            messages = build_messages(progress, current_step)
        full_history.append({"role": "user", "content": f"CURRENT STEP -- do this now: {current_step}"})
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
            full_history.append(result.message)
            continue

        if not tool_calls:
            json_retries += 1
            print(
                f"[turn {turn}] malformed tool-call JSON "
                f"(retry {json_retries}/{MAX_JSON_RETRIES})",
                flush=True,
            )
            full_history.append(result.message)
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

        full_history.append(result.message)
        full_history.append({"role": "tool", "content": str(step_output)})

        if turn == 0 and KILL_BEFORE_FIRST_SAVE:
            print("[kill] KILL_BEFORE_FIRST_SAVE -- exiting before any progress is saved", flush=True)
            os._exit(137)

        # Simplifying assumption for this project: one turn's worth of
        # tool calls satisfies one planned step. Update state in memory,
        # then hit disk BEFORE the next chat() call is made -- if the
        # process dies between here and the next turn, the resumed run
        # sees this step as done and doesn't repeat it.
        progress.steps_completed.append(current_step)
        progress.steps_remaining.pop(0)
        progress.last_tool_result = str(step_output)
        save_atomic(PROGRESS_PATH, progress)

        if KILL_AFTER_TURN is not None and turn == KILL_AFTER_TURN:
            print(f"[kill] KILL_AFTER_TURN={turn} -- exiting right after this turn's save", flush=True)
            os._exit(137)

    return False  # hit MAX_TURNS without finishing every planned step


def _dry_run_chat():
    """Scripted stand-in for chat(), gated behind HARNESS_DRY_RUN=1 --
    parses the CURRENT STEP text (DEFAULT_PLAN's or a seed_plan_of_length
    synthetic plan's, both fixed formats) and returns exactly the tool
    call that step asks for.

    Deliberately has NO memory of its own beyond what's actually present
    in `messages` this call -- when the final "write a summary" step
    needs an earlier file's content, it's recovered by scanning
    `messages` (including prior tool_calls arguments) for a surviving
    MARKER_n_CONTENT mention, never from an out-of-band cache. That's the
    whole point of the crossover-length comparison: structured mode's
    build_messages() re-includes every completed step's full text every
    turn, so it's always recoverable there; naive mode only keeps the
    last REPLAY_KEEP_LAST raw turns, so recovery genuinely fails once an
    early create-step's turn ages out of that window. A cache here would
    silently make both modes "work" and defeat the measurement.
    """

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        blob_parts = []
        for m in messages:
            content = m.get("content")
            if content:
                blob_parts.append(str(content))
            for call in m.get("tool_calls") or []:
                blob_parts.append(json.dumps(call))
        blob = " ".join(blob_parts)

        last_user = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        step_match = re.search(r"CURRENT STEP -- do this now: (.*)", last_user, re.DOTALL)
        step = step_match.group(1).strip() if step_match else last_user.strip()

        create_match = re.match(r"create (\S+\.txt) with (?:exactly this one-line content: (.+)|.*)", step)
        if create_match:
            filename, explicit_content = create_match.groups()
            content = explicit_content.strip() if explicit_content else f"placeholder content for {filename}"
            return ChatResult(
                message={
                    "role": "assistant",
                    "tool_calls": [
                        {"function": {"name": "write_file", "arguments": {"path": filename, "content": content}}}
                    ],
                },
                prompt_tokens=10,
                completion_tokens=10,
            )

        filenames = re.findall(r"\bfile(\d+)\.txt\b", step)
        recovered = []
        for idx in filenames:
            marker = f"MARKER_{idx}_CONTENT"
            recovered.append(marker if marker in blob else "")
        summary = "\n".join(recovered)
        return ChatResult(
            message={
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "write_file", "arguments": {"path": "summary.txt", "content": summary}}}
                ],
            },
            prompt_tokens=10,
            completion_tokens=10,
        )

    return fake_chat


if os.environ.get("HARNESS_DRY_RUN") == "1":
    chat = _dry_run_chat()
    log_token_usage = lambda *a, **kw: None  # noqa: E731


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or DEFAULT_TASK
    success = run(task)
    print("SUCCESS" if success else "FAILED (max turns)")
