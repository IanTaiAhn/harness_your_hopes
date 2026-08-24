"""Project 2: survive a restart.

Run once to start a task, hard-kill it mid-run with:
    taskkill /F /PID <pid>
then run again with the same task/progress-file path to resume.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01-bare-metal-loop"))
from tools import DISPATCH, TOOLS_SCHEMA  # noqa: E402

from state import Progress, load, save_atomic  # noqa: E402

MODEL = "qwen3.5:4b"
MAX_TURNS = 25
PROGRESS_PATH = Path(__file__).parent / "progress.json"


def run(task: str) -> bool:
    progress = load(PROGRESS_PATH)
    if progress is None:
        progress = Progress(task=task)
        # TODO: seed steps_remaining by asking the model to plan, or hardcode for the test task
    else:
        print(f"Resuming: {len(progress.steps_completed)} step(s) already done")

    for turn in range(MAX_TURNS):
        # TODO: same tool-call loop as Project 1, but after each completed step:
        #       move it from steps_remaining to steps_completed and
        #       save_atomic(PROGRESS_PATH, progress) BEFORE requesting the next turn —
        #       state must hit disk before you risk the next model call
        raise NotImplementedError

    return False


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "create 3 files, then a 4th that summarizes the first 3"
    success = run(task)
    print("SUCCESS" if success else "FAILED (max turns)")
