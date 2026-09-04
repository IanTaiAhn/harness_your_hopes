"""Drives 20 tasks through generate -> evaluate -> retry-with-feedback,
logging the self-reported vs. evaluator-verified gap. This is what
measurements/results.md gets filled in from.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import is_available  # noqa: E402

import generator  # noqa: E402
import render_results  # noqa: E402
from evaluator import evaluate_deterministic  # noqa: E402
from generator import generate  # noqa: E402

MAX_RETRIES = 2
TASKS_DIR = Path(__file__).parent / "tasks"
MEASUREMENTS_DIR = Path(__file__).parent / "measurements"


def _model_slug(model: str) -> str:
    return model.replace(":", "_").replace(".", "")


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


def main(argv: list[str] | None = None, skip_availability_check: bool = False) -> None:
    """skip_availability_check exists for tests (and any caller that has
    already confirmed Ollama is up) -- the real CLI entrypoint below
    always checks.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("HARNESS_MODEL", generator.MODEL))
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="skip regenerating measurements/results.md at the end",
    )
    args = parser.parse_args(argv)
    generator.MODEL = args.model

    if not skip_availability_check:
        ok, message = is_available(models=[args.model])
        if not ok:
            raise SystemExit(message)
        print(f"[run_suite] {message}, running as model={args.model}", flush=True)

    task_specs = sorted(TASKS_DIR.glob("*.json"))
    if not task_specs:
        raise SystemExit(f"no task specs found in {TASKS_DIR}")

    MEASUREMENTS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = MEASUREMENTS_DIR / f"runs_{_model_slug(args.model)}.jsonl"
    results = []
    for spec_path in task_specs:
        task_spec = json.loads(spec_path.read_text(encoding="utf-8"))
        result = run_one(task_spec)
        result["model"] = args.model
        results.append(result)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")
        print(
            f"{task_spec['id']}: self_reported={result['self_reported']} "
            f"verified={result['verified']} (attempt {result['attempt']})",
            flush=True,
        )

    total = len(results)
    self_reported_count = sum(1 for r in results if r["self_reported"])
    verified_count = sum(1 for r in results if r["verified"])
    print(f"\nmodel: {args.model}")
    print(f"self-reported success: {self_reported_count}/{total}")
    print(f"evaluator-verified success: {verified_count}/{total}")
    print(f"gap: {self_reported_count - verified_count}")

    if not args.no_render:
        render_results.main()


if __name__ == "__main__":
    main()
