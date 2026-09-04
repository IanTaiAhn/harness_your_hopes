"""Automates Project 1's Measure step: retry-on-malformed-JSON on vs.
off, 4B vs 9B, 10 trials each (40 total). Fills in measurements/results.md
from real trial data instead of by hand.

Run for real (needs Ollama running with qwen3.5:4b and qwen3.5:9b pulled):
    uv run python measure.py
    uv run python measure.py --models qwen3.5:4b --trials 3   # a quick subset

Validate the harness itself without a live model:
    uv run python measure.py --dry-run
"""
from __future__ import annotations

import argparse
import itertools
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.measure import append_jsonl, read_jsonl, update_results_md  # noqa: E402
from common.ollama_client import ChatResult, is_available  # noqa: E402

import agent  # noqa: E402

HERE = Path(__file__).parent
RUNS_LOG = HERE / "measurements" / "runs.jsonl"
RESULTS_MD = HERE / "measurements" / "results.md"

MODELS = ["qwen3.5:4b", "qwen3.5:9b"]
RETRY_CONFIGS = [("on", 2), ("off", 0)]
TRIALS_PER_CELL = 10
TASK = "read input.txt, count the lines, write the count to output.txt"


def _dry_run_chat():
    """Scripted fake chat(): one malformed-JSON turn, then a real
    read_file/write_file/finish happy path. Exists to prove the trial
    loop, jsonl logging, and results.md rendering below are correct
    before ever spending real Ollama time on them.
    """
    counter = itertools.count()

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        n = next(counter) % 4  # cycle so every trial gets the same 4-turn script
        if n == 0:
            return ChatResult(
                message={"role": "assistant", "content": "not valid json {"},
                prompt_tokens=10,
                completion_tokens=5,
            )
        if n == 1:
            return ChatResult(
                message={
                    "role": "assistant",
                    "tool_calls": [
                        {"function": {"name": "read_file", "arguments": {"path": "input.txt"}}}
                    ],
                },
                prompt_tokens=10,
                completion_tokens=5,
            )
        if n == 2:
            return ChatResult(
                message={
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "write_file",
                                "arguments": {"path": "output.txt", "content": "3"},
                            }
                        }
                    ],
                },
                prompt_tokens=10,
                completion_tokens=5,
            )
        return ChatResult(
            message={"role": "assistant", "content": "Done."}, prompt_tokens=5, completion_tokens=2
        )

    return fake_chat


def run_trial(model: str, retry_label: str, max_json_retries: int, trial_num: int, dry_run: bool) -> dict:
    agent.MODEL = model
    agent.MAX_JSON_RETRIES = max_json_retries
    if dry_run:
        agent.chat = _dry_run_chat()
        agent.log_token_usage = lambda *a, **kw: None

    with tempfile.TemporaryDirectory(prefix="p1-measure-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "input.txt").write_text("a\nb\nc\n", encoding="utf-8")
        prev_cwd = Path.cwd()
        os.chdir(tmp_path)
        diagnostics: dict = {}
        try:
            try:
                passed = agent.run(TASK, diagnostics=diagnostics)
            except Exception as e:
                passed = False
                diagnostics.setdefault("stop_reason", "exception")
                diagnostics["last_error"] = str(e)
        finally:
            os.chdir(prev_cwd)

    record = {"model": model, "retry": retry_label, "trial": trial_num, "passed": passed, **diagnostics}
    append_jsonl(RUNS_LOG, record)
    return record


def render_results_md() -> None:
    rows = read_jsonl(RUNS_LOG)
    cells: dict[tuple[str, str], list[bool]] = {}
    for row in rows:
        key = (row["model"].split(":")[-1], row["retry"])
        cells.setdefault(key, []).append(row["passed"])

    header = (
        "| Model | Retry logic | "
        + " | ".join(str(i) for i in range(1, TRIALS_PER_CELL + 1))
        + " | Pass rate |"
    )
    sep = "|" + "---|" * (TRIALS_PER_CELL + 3)
    lines = [header, sep]
    takeaway_bits = []
    for model in MODELS:
        model_short = model.split(":")[-1]
        rates = {}
        for retry_label, _ in RETRY_CONFIGS:
            results = cells.get((model_short, retry_label), [])
            marks = ["✓" if p else "✗" for p in results]
            padded = marks + [""] * (TRIALS_PER_CELL - len(marks))
            pass_rate = f"{sum(results)}/{len(results)}" if results else "—"
            lines.append(f"| {model_short} | {retry_label}  | " + " | ".join(padded) + f" | {pass_rate} |")
            if results:
                rates[retry_label] = sum(results) / len(results)
        if "on" in rates and "off" in rates:
            takeaway_bits.append(
                f"{model_short}: retry-on {rates['on']:.0%} vs retry-off {rates['off']:.0%} "
                f"(gap {rates['on'] - rates['off']:+.0%})"
            )

    takeaway = (
        "Auto-computed from measurements/runs.jsonl. " + "; ".join(takeaway_bits) + "."
        if takeaway_bits
        else "<!-- Fill in after all 40 trials: did retry logic matter more on the 4B than the 9B, as predicted? By how much? -->"
    )

    update_results_md(
        RESULTS_MD,
        {
            "task": f"Task used for all trials: `{TASK}`",
            "retry-table": "\n".join(lines),
            "takeaway": takeaway,
        },
    )


def main() -> None:
    global TRIALS_PER_CELL
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=MODELS)
    parser.add_argument("--trials", type=int, default=TRIALS_PER_CELL)
    parser.add_argument("--dry-run", action="store_true", help="fake chat(), no Ollama needed")
    args = parser.parse_args()

    if not args.dry_run:
        ok, message = is_available(models=args.models)
        if not ok:
            raise SystemExit(f"{message}\nRun with --dry-run to validate the harness without Ollama.")
        print(f"[measure] {message}", flush=True)

    TRIALS_PER_CELL = args.trials

    for model in args.models:
        for retry_label, max_json_retries in RETRY_CONFIGS:
            for trial_num in range(1, args.trials + 1):
                record = run_trial(model, retry_label, max_json_retries, trial_num, args.dry_run)
                print(
                    f"[{model} retry={retry_label} trial {trial_num}/{args.trials}] "
                    f"passed={record['passed']} stop_reason={record.get('stop_reason')}",
                    flush=True,
                )

    render_results_md()
    print(f"\nWrote {RUNS_LOG} and regenerated {RESULTS_MD}", flush=True)


if __name__ == "__main__":
    main()
