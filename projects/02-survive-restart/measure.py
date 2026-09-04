"""Automates Project 2's two Measure tables.

Kill-point resume test: instead of a manual `taskkill`/`kill -9` timed by
hand (which can't land at a precise turn boundary without a race),
KILL_AFTER_TURN/KILL_BEFORE_FIRST_SAVE in agent.py make the process
hard-exit (os._exit -- skips cleanup exactly like an external kill would)
at 5 deterministic points across DEFAULT_TASK's 4 steps, then a normal
rerun is checked for a clean, non-duplicated resume. This half needs no
Ollama in --dry-run mode and barely any even for real (each kill point is
1-2 real turns).

Structured file vs. naive replay crossover length: drives both
HARNESS_REPLAY_MODE settings against seed_plan_of_length(n) synthetic
tasks (n in 5/10/15/20/25 steps), checking the result with
check_synthetic_summary() -- a plain string check, no model judgment
needed to score "correct".

Run for real (needs Ollama + qwen3.5:4b for the crossover half):
    uv run python measure.py

Validate the harness itself without Ollama:
    uv run python measure.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.measure import append_jsonl, read_jsonl, update_results_md  # noqa: E402
from common.ollama_client import is_available  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01-bare-metal-loop"))
sys.path.insert(0, str(Path(__file__).parent))
import agent  # noqa: E402

HERE = Path(__file__).parent
KILL_LOG = HERE / "measurements" / "kill_trials.jsonl"
CROSSOVER_LOG = HERE / "measurements" / "crossover_trials.jsonl"
RESULTS_MD = HERE / "measurements" / "results.md"
MODEL = "qwen3.5:4b"

# (label, env overrides) -- 5 distinct points across DEFAULT_TASK's 4
# steps: one mid-first-step (before any progress is ever saved), then one
# right after each of the 4 steps' own save.
KILL_POINTS = [
    ("1: mid first step, before any save", {"KILL_BEFORE_FIRST_SAVE": "1"}),
    ("2: right after step 1 saved", {"KILL_AFTER_TURN": "0"}),
    ("3: right after step 2 saved", {"KILL_AFTER_TURN": "1"}),
    ("4: right after step 3 saved", {"KILL_AFTER_TURN": "2"}),
    ("5: right after step 4 saved", {"KILL_AFTER_TURN": "3"}),
]
CROSSOVER_LENGTHS = [5, 10, 15, 20, 25]


def _run_agent(cwd: Path, env_overrides: dict, task: str | None, dry_run: bool) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "HARNESS_MODEL": MODEL,
        **env_overrides,
        "HARNESS_PROGRESS_PATH": str(cwd / "progress.json"),
    }
    # A synthetic n-step task needs n+1 turns (n creates + 1 summary) --
    # agent.py's default MAX_TURNS=25 would otherwise silently cap out
    # and get misread as "lost track" at exactly the largest length
    # tried, when it's actually an unrelated turn-limit artifact.
    if task and task.startswith(agent.SYNTHETIC_TASK_PREFIX):
        n = int(task[len(agent.SYNTHETIC_TASK_PREFIX):])
        env.setdefault("HARNESS_MAX_TURNS", str(n + 5))
    if dry_run:
        env["HARNESS_DRY_RUN"] = "1"
    args = [sys.executable, str(HERE / "agent.py")]
    if task:
        args.append(task)
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=300)


def run_kill_trial(label: str, kill_env: dict, dry_run: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="p2-kill-") as tmp:
        cwd = Path(tmp)
        killed = _run_agent(cwd, kill_env, None, dry_run)
        resumed = _run_agent(cwd, {}, None, dry_run)

        progress_path = cwd / "progress.json"
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
        completed = progress.get("steps_completed", [])
        expected = list(agent.DEFAULT_PLAN)
        files_present = all((cwd / f"file{i}.txt").is_file() for i in range(1, 4)) and (cwd / "summary.txt").is_file()

        clean = (
            "SUCCESS" in resumed.stdout
            and completed == expected  # every step exactly once, right order, no repeats
            and files_present
        )
        notes = (
            f"killed exit={killed.returncode}, resumed exit={resumed.returncode}, "
            f"steps_completed={len(completed)}/{len(expected)}, no-repeat={completed == expected}, "
            f"files_present={files_present}"
        )

    record = {"kill_point": label, "resumed_cleanly": clean, "notes": notes, "dry_run": dry_run}
    append_jsonl(KILL_LOG, record)
    print(f"[kill {label}] resumed_cleanly={clean} — {notes}", flush=True)
    return record


def run_crossover_trial(n: int, mode: str, dry_run: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="p2-crossover-") as tmp:
        cwd = Path(tmp)
        env = {"HARNESS_REPLAY_MODE": mode}
        proc = _run_agent(cwd, env, f"synthetic:{n}", dry_run)
        summary_path = cwd / "summary.txt"
        summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""
        correct = "SUCCESS" in proc.stdout and agent.check_synthetic_summary(summary, n)

    record = {"length": n, "mode": mode, "correct": correct, "dry_run": dry_run}
    append_jsonl(CROSSOVER_LOG, record)
    print(f"[crossover n={n} mode={mode}] correct={correct}", flush=True)
    return record


def render_results_md() -> None:
    kill_rows = read_jsonl(KILL_LOG)
    by_point = {r["kill_point"]: r for r in kill_rows}
    kill_lines = ["| Kill point (turn #) | Resumed cleanly? | Notes |", "|---|---|---|"]
    for label, _ in KILL_POINTS:
        r = by_point.get(label)
        num = label.split(":")[0]
        if r is None:
            kill_lines.append(f"| {num} | | |")
        else:
            kill_lines.append(f"| {num} | {'✓' if r['resumed_cleanly'] else '✗'} | {r['notes']} |")

    crossover_rows = read_jsonl(CROSSOVER_LOG)
    by_len_mode = {(r["length"], r["mode"]): r["correct"] for r in crossover_rows}
    crossover_lines = [
        "| Task length (turns) | Structured file: correct? | Replay-last-N: correct? |",
        "|---|---|---|",
    ]
    crossover_point = None
    for n in CROSSOVER_LENGTHS:
        structured = by_len_mode.get((n, "structured"))
        naive = by_len_mode.get((n, "naive"))
        if crossover_point is None and naive is False:
            crossover_point = n
        s_mark = "" if structured is None else ("✓" if structured else "✗")
        n_mark = "" if naive is None else ("✓" if naive else "✗")
        crossover_lines.append(f"| {n} | {s_mark} | {n_mark} |")

    takeaway = (
        f"Auto-computed from measurements/*.jsonl. Kill-point resume: "
        f"{sum(1 for r in kill_rows if r['resumed_cleanly'])}/{len(kill_rows)} points resumed cleanly. "
        + (
            f"Naive replay first failed at task length {crossover_point}."
            if crossover_point is not None
            else "Naive replay hasn't failed within the lengths tried yet (or hasn't been run)."
        )
        if kill_rows or crossover_rows
        else "<!-- Fill in: how much context/turns can naive replay tolerate before it loses track, on the 4B? -->"
    )

    update_results_md(
        RESULTS_MD,
        {
            "kill-table": "\n".join(kill_lines),
            "crossover-table": "\n".join(crossover_lines),
            "crossover-point": f"Crossover point (replay starts failing): `{crossover_point if crossover_point is not None else '______'}`",
            "takeaway": takeaway,
        },
    )


def main() -> None:
    global MODEL
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("HARNESS_MODEL", MODEL))
    parser.add_argument("--dry-run", action="store_true", help="fake chat(), no Ollama needed")
    parser.add_argument("--skip-kill", action="store_true")
    parser.add_argument("--skip-crossover", action="store_true")
    args = parser.parse_args()
    MODEL = args.model

    # Kill trials call real chat() too (unless --dry-run) -- this check
    # covers both halves, not just the crossover one.
    if not args.dry_run:
        ok, message = is_available(models=[MODEL])
        if not ok:
            raise SystemExit(f"{message}\nRun with --dry-run to validate the harness without Ollama.")
        print(f"[measure] {message}", flush=True)

    if not args.skip_kill:
        for label, kill_env in KILL_POINTS:
            run_kill_trial(label, kill_env, args.dry_run)

    if not args.skip_crossover:
        for n in CROSSOVER_LENGTHS:
            for mode in ("structured", "naive"):
                run_crossover_trial(n, mode, args.dry_run)

    render_results_md()
    print(f"\nWrote {KILL_LOG} / {CROSSOVER_LOG} and regenerated {RESULTS_MD}", flush=True)


if __name__ == "__main__":
    main()
