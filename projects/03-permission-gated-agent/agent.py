"""Project 3: permission-gated file agent.

Task: organize/rename files in a real messy folder, staying inside
`WORKSPACE_ROOT`. Every tool call goes through policy.Allowlist.check()
and audit.record() before it executes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import chat, log_token_usage  # noqa: E402

from audit import record  # noqa: E402
from policy import Allowlist, PolicyViolation  # noqa: E402

MODEL = "qwen3.5:4b"
WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", str(Path(__file__).parent / "sandbox"))
AUDIT_LOG = Path(__file__).parent / "measurements" / "audit.jsonl"

allowlist = Allowlist([WORKSPACE_ROOT])


def gated_call(action: str, path: str, fn, *args, **kwargs):
    try:
        resolved = allowlist.check(path)
        if allowlist.requires_confirmation(action):
            # TODO: prompt for manual confirmation before proceeding
            pass
        result = fn(resolved, *args, **kwargs)
        record(AUDIT_LOG, action, path, allowed=True)
        return result
    except PolicyViolation as e:
        record(AUDIT_LOG, action, path, allowed=False, reason=str(e))
        raise


def run(task: str) -> bool:
    # TODO: same tool-call loop as Project 1/2, but every tool dispatch
    #       goes through gated_call() instead of calling DISPATCH directly
    raise NotImplementedError


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "organize the files in the workspace by extension"
    success = run(task)
    print("SUCCESS" if success else "FAILED")
