"""Runs fresh every invocation — no in-memory state survives between
runs. Reads feature_list.json + git log FIRST, picks ONE unfinished
feature, implements + tests + commits it, then exits.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

MODEL = "qwen3.5:4b"
TARGET = Path(__file__).parent / "target"


def read_state() -> tuple[dict, str]:
    feature_list = json.loads((TARGET / "feature_list.json").read_text(encoding="utf-8"))
    git_log = subprocess.run(
        ["git", "log", "--oneline"], cwd=TARGET, capture_output=True, text=True, check=True
    ).stdout
    return feature_list, git_log


def pick_feature(feature_list: dict) -> str | None:
    unfinished = [name for name, done in feature_list.items() if not done]
    return unfinished[0] if unfinished else None


def main() -> None:
    feature_list, git_log = read_state()
    feature = pick_feature(feature_list)
    if feature is None:
        print("All features complete.")
        return

    print(f"Working on: {feature}")
    # TODO: run the tool loop (reuse Project 1/2's pattern) to implement
    # `feature` inside TARGET, using `git_log` as context for what already
    # exists. Test it (pytest subprocess / curl.exe against a fixed port —
    # no browser automation).
    #
    # TODO: reuse Project 4's evaluator here — do NOT trust the model's
    # own "I'm done" claim as the commit trigger. Only mark the feature
    # done in feature_list.json and commit if the test actually passes.
    raise NotImplementedError

    # TODO: on verified success:
    #   feature_list[feature] = True
    #   (TARGET / "feature_list.json").write_text(json.dumps(feature_list, indent=2))
    #   subprocess.run(["git", "add", "-A"], cwd=TARGET, check=True)
    #   subprocess.run(["git", "commit", "-m", f"Implement: {feature}"], cwd=TARGET, check=True)


if __name__ == "__main__":
    main()
