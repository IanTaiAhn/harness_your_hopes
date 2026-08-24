"""Evaluator role: the only source of truth for success/failure.

Deterministic first — a pytest run is free and exact. Fall back to a
second model call only when the task's criterion genuinely can't be
expressed as a test (e.g. "is this explanation clear").
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    passed: bool
    feedback: str  # specific: failing test name + assertion, not just "failed"


def evaluate_deterministic(test_path: Path) -> EvalResult:
    # TODO: subprocess.run([sys.executable, "-m", "pytest", str(test_path), "-v"],
    #       capture_output=True, text=True, timeout=60)
    #       EvalResult(passed=(returncode == 0), feedback=<last failing assertion from stdout>)
    raise NotImplementedError


def evaluate_judge(task: str, solution_summary: str) -> EvalResult:
    # TODO: only for criteria a test can't express — a second, cheap model
    # call scoring pass/fail with a one-line reason
    raise NotImplementedError
