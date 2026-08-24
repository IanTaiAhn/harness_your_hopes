"""Project 1: bare-metal tool loop.

Run: .venv\\Scripts\\python.exe agent.py "read this file, count the lines,
write the count to a new file"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

from tools import DISPATCH, TOOLS_SCHEMA  # noqa: E402

MODEL = "qwen3.5:4b"
MAX_TURNS = 15
MAX_JSON_RETRIES = 2  # toggle this to 0 for the Project 1 "measure" ablation


def run(task: str) -> bool:
    messages = [
        {"role": "system", "content": "You are a careful local coding agent."},
        {"role": "user", "content": task},
    ]
    log_path = Path(__file__).parent / "measurements" / "tokens.jsonl"

    for turn in range(MAX_TURNS):
        # TODO: call chat(MODEL, messages, tools=TOOLS_SCHEMA), log_token_usage(...)
        # TODO: if the model's tool-call JSON fails to parse, append the parse
        #       error as a tool-role message and retry, up to MAX_JSON_RETRIES —
        #       this is the block Project 1's "measure" step ablates
        # TODO: if no tool call and the model appears to consider the task done,
        #       return True
        # TODO: else, dispatch via DISPATCH[name](**args), append the result as
        #       a tool-role message, continue the loop
        raise NotImplementedError

    return False  # hit MAX_TURNS without a clean finish


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "read this file, count the lines, write the count to a new file"
    success = run(task)
    print("SUCCESS" if success else "FAILED (max turns)")
