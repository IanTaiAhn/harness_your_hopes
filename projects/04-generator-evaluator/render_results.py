"""Regenerates measurements/results.md from measurements/runs_<model>.jsonl.

Standalone from run_suite.py (which also calls this at the end of a run)
so results.md can be rebuilt from whatever real runs already exist on
disk without re-running the suite, e.g. after only the 4B run has
happened so far.

Run: uv run python render_results.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.measure import update_results_md  # noqa: E402

HERE = Path(__file__).parent
MEASUREMENTS_DIR = HERE / "measurements"
RESULTS_MD = MEASUREMENTS_DIR / "results.md"
TASKS_DIR = HERE / "tasks"

# (marker key, model, short label) — the two runs this project's Measure
# step asks for. Extend this list if a third model is ever compared.
MODEL_SECTIONS = [
    ("run-4b", "qwen3.5:4b", "4B"),
    ("run-9b", "qwen3.5:9b", "9B"),
]


def _slug(model: str) -> str:
    return model.replace(":", "_").replace(".", "")


def _load_runs(model: str) -> dict[str, dict]:
    path = MEASUREMENTS_DIR / f"runs_{_slug(model)}.jsonl"
    if not path.exists():
        return {}
    # A task can appear more than once if run_suite.py was re-run — keep
    # the most recent record per task id.
    by_task: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                by_task[record["task"]] = record
    return by_task


def render_section(model: str, label: str) -> str:
    runs = _load_runs(model)
    task_ids = sorted(
        p.stem for p in TASKS_DIR.glob("task_*.json")
    ) or sorted(runs.keys())

    if not runs:
        return (
            f"No runs recorded yet for `{model}`. Run "
            f"`uv run python run_suite.py --model {model}`."
        )

    lines = [
        "| Task | Self-reported success | Evaluator-verified success | Retries used |",
        "|---|---|---|---|",
    ]
    for task_id in task_ids:
        r = runs.get(task_id)
        if r is None:
            lines.append(f"| {task_id} | (not run) | (not run) | |")
            continue
        lines.append(
            f"| {task_id} | {'✓' if r['self_reported'] else '✗'} "
            f"| {'✓' if r['verified'] else '✗'} | {r['attempt']} |"
        )

    total = len(runs)
    self_reported = sum(1 for r in runs.values() if r["self_reported"])
    verified = sum(1 for r in runs.values() if r["verified"])
    lines.append("")
    lines.append(f"Self-reported success rate: `{self_reported}/{total}`")
    lines.append(f"Evaluator-verified success rate: `{verified}/{total}`")
    lines.append(f"**Gap: `{self_reported - verified}`**")
    return "\n".join(lines)


def main() -> None:
    sections = {key: render_section(model, label) for key, model, label in MODEL_SECTIONS}

    fours = _load_runs("qwen3.5:4b")
    nines = _load_runs("qwen3.5:9b")
    if fours and nines:
        gap4 = sum(1 for r in fours.values() if r["self_reported"]) - sum(
            1 for r in fours.values() if r["verified"]
        )
        gap9 = sum(1 for r in nines.values() if r["self_reported"]) - sum(
            1 for r in nines.values() if r["verified"]
        )
        sections["takeaway"] = (
            f"Auto-computed from measurements/runs_*.jsonl. Self-report/verified gap: "
            f"4B={gap4}, 9B={gap9} ("
            + ("gap narrows on the 9B" if gap9 < gap4 else "gap does not narrow on the 9B")
            + f" — {gap4} -> {gap9})."
        )
    else:
        sections["takeaway"] = (
            "<!-- Fill in once both the 4B and 9B runs exist: does the gap narrow on the 9B? By how much? -->"
        )

    update_results_md(RESULTS_MD, sections)
    print(f"Regenerated {RESULTS_MD}", flush=True)


if __name__ == "__main__":
    main()
