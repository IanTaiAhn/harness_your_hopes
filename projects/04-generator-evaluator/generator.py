"""Generator role: produces a solution, self-reports done/not-done.

The self-report is deliberately trusted nowhere else in this project —
evaluator.py is the only source of truth for whether a task actually
succeeded.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

MODEL = "qwen3.5:4b"


def generate(task: str, feedback: str | None = None) -> tuple[str, bool]:
    """Returns (solution_code_or_summary, self_reported_success).

    TODO: build messages (include `feedback` from a prior evaluator
    rejection if present), run the Project 1/2 tool loop to write the
    solution to disk, and parse the model's own final "done" claim
    into self_reported_success.
    """
    raise NotImplementedError
