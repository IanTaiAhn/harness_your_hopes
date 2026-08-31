"""Runs once. Sets up target/ with a feature list, CONTRACT.md, the
fixed ground-truth test suite, an init script, and a first commit.
Everything after this is coding_agent.py's job -- this script never
writes a line of todo.py itself.

Run (from this directory): uv run python initializer.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from contract import CLI_CONTRACT, FEATURES

HERE = Path(__file__).parent
TARGET = HERE / "target"
TESTS_TEMPLATE = HERE / "tests_template"


def main() -> None:
    if (TARGET / ".git").exists():
        raise SystemExit(f"{TARGET} is already initialized -- remove it first if you want to restart.")

    TARGET.mkdir(exist_ok=True)

    feature_list = {name: False for name, _ in FEATURES}
    (TARGET / "feature_list.json").write_text(
        json.dumps(feature_list, indent=2), encoding="utf-8"
    )

    (TARGET / "CONTRACT.md").write_text(CLI_CONTRACT, encoding="utf-8")

    # init.ps1, NOT init.sh -- say so in coding_agent.py's own prompt too,
    # or a model will reach for bash out of habit and never notice it
    # doesn't run on this target.
    shutil.copy(HERE / "init.ps1", TARGET / "init.ps1")

    tests_dst = TARGET / "tests"
    if tests_dst.exists():
        shutil.rmtree(tests_dst)
    shutil.copytree(TESTS_TEMPLATE, tests_dst)

    subprocess.run(["git", "init"], cwd=TARGET, check=True)
    # Before the first commit, or line-ending churn on Windows makes
    # every diff look enormous and the git-log handoff signal becomes
    # noise -- see the main doc's Project 5 section.
    subprocess.run(["git", "config", "core.autocrlf", "true"], cwd=TARGET, check=True)
    subprocess.run(["git", "add", "-A"], cwd=TARGET, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initialize feature list, CONTRACT.md, and test suite"],
        cwd=TARGET,
        check=True,
    )
    print(f"Initialized {TARGET} with {len(feature_list)} features, all pending.")


if __name__ == "__main__":
    main()
