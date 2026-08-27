"""Evaluator role: the only source of truth for success/failure.

Deterministic first — a pytest run is free and exact. Fall back to a
second model call only when the task's criterion genuinely can't be
expressed as a test (e.g. "is this explanation clear").
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    passed: bool
    feedback: str  # specific: failing test name + assertion, not just "failed"


def _failure_feedback(stdout: str) -> str:
    """Pull the failing test name + assertion out of `pytest -v` output —
    the retry loop needs something the generator can act on, not just a
    bare "failed".
    """
    lines = stdout.splitlines()
    failed_lines = [line.strip() for line in lines if line.startswith("FAILED")]
    assertion_lines = [
        line.strip()
        for line in lines
        if line.strip().startswith(("assert", "E "))
    ]
    parts = failed_lines[-1:] + assertion_lines[-1:]
    if parts:
        return " | ".join(parts)
    return stdout[-500:].strip() or "pytest produced no output"


def evaluate_deterministic(test_path: Path) -> EvalResult:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return EvalResult(passed=False, feedback="evaluator timed out after 60s")

    passed = result.returncode == 0
    feedback = "all tests passed" if passed else _failure_feedback(result.stdout)
    return EvalResult(passed=passed, feedback=feedback)


def evaluate_judge(task: str, solution_summary: str) -> EvalResult:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from common.ollama_client import chat  # noqa: E402

    judge_model = "qwen3.5:4b"
    prompt = (
        f"Task: {task}\n\nSolution summary: {solution_summary}\n\n"
        "Does this solution genuinely satisfy the task? Reply with exactly "
        "one line: 'PASS: <one-sentence reason>' or 'FAIL: <one-sentence "
        "reason>'."
    )
    result = chat(judge_model, [{"role": "user", "content": prompt}])
    content = (result.message.get("content") or "").strip()
    passed = content.upper().startswith("PASS")
    return EvalResult(passed=passed, feedback=content or "judge returned no response")
