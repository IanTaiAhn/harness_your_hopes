"""Shared fixtures for the target CLI's test suite.

This directory is copied verbatim into target/tests/ by initializer.py
-- target/ is gitignored (it's the coding agent's own nested git repo),
so this template is the tracked, reproducible source of the ground-truth
tests. `collect_ignore_glob` keeps a repo-wide `uv run pytest` here from
running (or failing on) copies of a CLI that doesn't exist at this path;
coding_agent.py's evaluate step runs the copies under target/tests/
directly by path instead, same pattern as Project 4's tasks/conftest.py.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

collect_ignore_glob = ["test_*.py"]

# Once copied into target/tests/, this resolves to target/ -- the
# directory holding todo.py.
TARGET = Path(__file__).resolve().parent.parent


@pytest.fixture
def store(tmp_path):
    return tmp_path / "todos.json"


@pytest.fixture
def cli(store):
    """Invoke todo.py exactly as the contract specifies: `uv run python
    todo.py ... --store <path>`, never relying on inherited PATH. Each
    test gets its own --store, so tests can run in any order without
    interfering with each other.
    """

    def _run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["uv", "run", "python", "todo.py", *args, "--store", str(store)],
            cwd=TARGET,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return _run
