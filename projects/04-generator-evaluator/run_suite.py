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
    # TODO: load task specs from TASKS_DIR/*.json, run_one() each,
    # append results to LOG_PATH, print the self-reported vs. verified
    # success-rate gap at the end
    raise NotImplementedError


if __name__ == "__main__":
    main()
