"""Shared fixture for the ground-truth task checks in this directory.

`collect_ignore_glob` keeps a repo-wide `uv run pytest` from failing on
these — they are the evaluator's fixtures, not tests of our own code, and
fail by design until a generator run has actually written a solution.
`evaluate_deterministic()` in ../evaluator.py runs each one directly by
path, where `collect_ignore_glob` does not apply (see the test in
../test_evaluator.py that pins this down).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

collect_ignore_glob = ["test_task_*.py"]

SOLUTIONS_DIR = Path(__file__).parent / "solutions"


@pytest.fixture
def load_solution():
    def _load(task_id: str):
        path = SOLUTIONS_DIR / f"{task_id}.py"
        assert path.is_file(), f"generator did not write {path}"
        spec = importlib.util.spec_from_file_location(task_id, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return _load
