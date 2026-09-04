"""Automates Project 5's Measure step: baseline + the 3 ablations from
README.md, each driving `--iterations` genuinely fresh `coding_agent.py`
subprocesses (real process boundaries, same as `run_loop.ps1`), tracking
iterations-to-a-working-app, git history shape, and the specific failure
mode per ablation. Fills in measurements/results.md from real data
instead of by hand.

Run for real (needs Ollama + qwen3.5:4b pulled — this is expensive: 4
configs x 10 sessions by default):
    uv run python measure.py
    uv run python measure.py --configs baseline --iterations 3   # a cheap subset

Validate the harness itself without a live model (scripted reference
todo.py that satisfies every ground-truth test):
    uv run python measure.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.measure import append_jsonl, read_jsonl, update_results_md  # noqa: E402
from common.ollama_client import is_available  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "04-generator-evaluator"))
from evaluator import evaluate_deterministic  # noqa: E402

from contract import TEST_FILES  # noqa: E402

HERE = Path(__file__).parent
TARGET = HERE / "target"
RUNS_LOG = HERE / "measurements" / "runs.jsonl"
RESULTS_MD = HERE / "measurements" / "results.md"

CONFIGS = {
    "baseline": {},
    "no_feature_list": {"ABLATE_NO_FEATURE_LIST": "1"},
    "no_gitlog": {"ABLATE_NO_GITLOG": "1"},
    "no_commit": {"ABLATE_NO_COMMIT": "1"},
}
DEFAULT_ITERATIONS = 10
MODEL = "qwen3.5:4b"


def reset_target() -> None:
    if TARGET.exists():
        shutil.rmtree(TARGET)
    subprocess.run([sys.executable, "initializer.py"], cwd=HERE, check=True, capture_output=True, text=True)


def tests_status() -> dict[str, bool]:
    return {
        name: evaluate_deterministic(TARGET / "tests" / filename).passed
        for name, filename in TEST_FILES.items()
    }


def commit_count() -> int:
    result = subprocess.run(
        ["git", "log", "--oneline"], cwd=TARGET, capture_output=True, text=True
    )
    if result.returncode != 0:
        return 0
    return len([line for line in result.stdout.splitlines() if line.strip()])


def run_config(label: str, overrides: dict, iterations: int, dry_run: bool) -> dict:
    reset_target()
    env = {**os.environ, **overrides}
    if dry_run:
        env["HARNESS_DRY_RUN"] = "1"

    history = []
    done_at = None
    for i in range(1, iterations + 1):
        proc = subprocess.run(
            [sys.executable, "coding_agent.py"],
            cwd=HERE,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        tests = tests_status()
        commits = commit_count()
        all_done = all(tests.values())
        if done_at is None and all_done:
            done_at = i
        history.append(
            {
                "iteration": i,
                "tests_passing": sum(tests.values()),
                "commits": commits,
                "stdout_last_line": proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "",
                "stderr_tail": proc.stderr.strip()[-500:] if proc.returncode != 0 else "",
            }
        )
        print(
            f"[{label} iter {i}/{iterations}] tests_passing={sum(tests.values())}/{len(tests)} "
            f"commits={commits}",
            flush=True,
        )

    final_tests = tests_status()
    final_commits = commit_count()

    failure_mode = None
    if done_at is None:
        failure_mode = (
            f"never reached all-tests-passing within {iterations} iterations "
            f"(ended at {sum(final_tests.values())}/{len(final_tests)})"
        )
    elif overrides.get("ABLATE_NO_COMMIT") == "1":
        failure_mode = (
            f"all {len(final_tests)} features verified (done at iteration {done_at}) but git history "
            f"never advanced past the initializer's first commit ({final_commits} total commit(s)) — "
            "feature_list.json is still updated on disk without a commit, so the harness's own "
            "progress record silently diverges from git history, its supposed source of truth"
        )
    elif overrides.get("ABLATE_NO_FEATURE_LIST") == "1":
        wasted = iterations - done_at
        if wasted > 0:
            failure_mode = (
                f"reached all-tests-passing at iteration {done_at}, but nothing in the harness "
                f"itself (no feature_list.json, and 'All features complete.' is only ever printed "
                f"in feature-list mode) can tell it's done — {wasted} more session(s) ran anyway, "
                "re-deriving progress from git log + reading todo.py every time with no signal to stop"
            )

    record = {
        "config": label,
        "dry_run": dry_run,
        "iterations": iterations,
        "iterations_to_done": done_at,
        "final_tests_passing": sum(final_tests.values()),
        "total_tests": len(final_tests),
        "final_commits": final_commits,
        "failure_mode": failure_mode,
        "history": history,
    }
    append_jsonl(RUNS_LOG, record)
    return record


def render_results_md() -> None:
    rows = read_jsonl(RUNS_LOG)
    latest = {}
    for r in rows:
        latest[r["config"]] = r  # last write per config wins

    def done_str(r: dict) -> str:
        if r["iterations_to_done"] is None:
            return f"not reached within {r['iterations']} iterations"
        return str(r["iterations_to_done"])

    def baseline_section() -> str:
        r = latest.get("baseline")
        if r is None:
            return "(not run yet)"
        expected_commits = 1 + r["total_tests"]  # initializer commit + one per feature
        clean = r["final_commits"] == expected_commits
        return (
            f"Iterations to a working app: `{done_str(r)}`\n"
            f"Clean git history (one commit/feature)? `{clean}` "
            f"({r['final_commits']} total commits, expected {expected_commits})"
        )

    def ablation_section(key: str) -> str:
        r = latest.get(key)
        if r is None:
            return "(not run yet)"
        return (
            f"Iterations to working app (or failure point): `{done_str(r)}`\n"
            f"Failure mode observed: `{r['failure_mode'] or '(none observed — behaved the same as baseline)'}`"
        )

    sections = {
        "baseline": baseline_section(),
        "no_feature_list": ablation_section("no_feature_list"),
        "no_gitlog": ablation_section("no_gitlog"),
        "no_commit": ablation_section("no_commit"),
    }

    if all(k in latest for k in CONFIGS):
        worst = max(
            (k for k in CONFIGS if k != "baseline"),
            key=lambda k: (
                latest[k]["iterations_to_done"] is None,
                latest[k]["iterations_to_done"] or 0,
            ),
        )
        sections["takeaway"] = (
            "Auto-computed from measurements/runs.jsonl. Baseline reached all tests passing at "
            f"iteration {done_str(latest['baseline'])}. Ablation results: "
            + "; ".join(f"{k}={done_str(latest[k])}" for k in CONFIGS if k != "baseline")
            + f". Slowest/worst-broken ablation: `{worst}` — {latest[worst]['failure_mode'] or 'no distinct failure mode observed'}."
        )
    else:
        missing = [k for k in CONFIGS if k not in latest]
        sections["takeaway"] = f"<!-- Still missing: {', '.join(missing)}. Run measure.py for each. -->"

    update_results_md(RESULTS_MD, sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS), choices=list(CONFIGS))
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--dry-run", action="store_true", help="scripted reference model, no Ollama")
    args = parser.parse_args()

    if not args.dry_run:
        ok, message = is_available(models=[MODEL])
        if not ok:
            raise SystemExit(f"{message}\nRun with --dry-run to validate the harness without Ollama.")
        print(f"[measure] {message}", flush=True)

    for label in args.configs:
        run_config(label, CONFIGS[label], args.iterations, args.dry_run)

    render_results_md()
    print(f"\nWrote {RUNS_LOG} and regenerated {RESULTS_MD}", flush=True)


if __name__ == "__main__":
    main()
