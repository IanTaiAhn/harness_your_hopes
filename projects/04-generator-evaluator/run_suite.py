"""Drives 20 tasks through generate -> evaluate -> retry-with-feedback,
logging the self-reported vs. evaluator-verified gap. This is what
measurements/results.md gets filled in from.
"""
from __future__ import annotations

import json
from pathlib import Path

from evaluator import evaluate_deterministic
from generator import generate

MAX_RETRIES = 2
TASKS_DIR = Path(__file__).parent / "tasks"
LOG_PATH = Path(__file__).parent / "measurements" / "runs.jsonl"


def run_one(task_spec: dict) -> dict:
    feedback = None
    for attempt in range(MAX_RETRIES + 1):
        solution, self_reported = generate(task_spec["prompt"], feedback=feedback)
        result = evaluate_deterministic(TASKS_DIR / task_spec["test_file"])
        if result.passed:
            return {
                "task": task_spec["id"],
                "attempt": attempt,
                "self_reported": self_reported,
                "verified": True,
            }
        feedback = result.feedback
    return {
        "task": task_spec["id"],
        "attempt": MAX_RETRIES,
        "self_reported": self_reported,
        "verified": False,
    }


def main() -> None:
    task_specs = sorted(TASKS_DIR.glob("*.json"))
    if not task_specs:
        raise SystemExit(f"no task specs found in {TASKS_DIR}")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for spec_path in task_specs:
        task_spec = json.loads(spec_path.read_text(encoding="utf-8"))
        result = run_one(task_spec)
        results.append(result)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
        print(
            f"{task_spec['id']}: self_reported={result['self_reported']} "
            f"verified={result['verified']} (attempt {result['attempt']})",
            flush=True,
        )

    total = len(results)
    self_reported_count = sum(1 for r in results if r["self_reported"])
    verified_count = sum(1 for r in results if r["verified"])
    print(f"\nself-reported success: {self_reported_count}/{total}")
    print(f"evaluator-verified success: {verified_count}/{total}")
    print(f"gap: {self_reported_count - verified_count}")


if __name__ == "__main__":
    main()
