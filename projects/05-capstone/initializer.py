"""Runs once. Sets up target/ with a feature list, an init script, and
a first commit. Everything after this is coding_agent.py's job.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

TARGET = Path(__file__).parent / "target"

FEATURES = [
    # TODO: pick your target app (CLI to-do / small Flask app) and list
    # its features here, e.g. "add item", "list items", "mark done",
    # "delete item", "persist to file"
]


def main() -> None:
    TARGET.mkdir(exist_ok=True)

    feature_list = {name: False for name in FEATURES}
    (TARGET / "feature_list.json").write_text(
        json.dumps(feature_list, indent=2), encoding="utf-8"
    )

    # TODO: write init.ps1 (NOT init.sh) — whatever bootstraps the target
    # app (venv, install deps, etc.)
    (TARGET / "init.ps1").write_text("# TODO\n", encoding="utf-8")

    # TODO: git init in TARGET, `git config core.autocrlf true` BEFORE
    # the first commit, then commit feature_list.json + init.ps1
    subprocess.run(["git", "init"], cwd=TARGET, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "true"], cwd=TARGET, check=True)
    subprocess.run(["git", "add", "-A"], cwd=TARGET, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initialize feature list and init script"],
        cwd=TARGET,
        check=True,
    )


if __name__ == "__main__":
    main()
