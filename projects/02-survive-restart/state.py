"""Structured progress file: read/write with atomic replace.

A half-written JSON file after a hard kill is exactly the failure this
project exists to prevent — always write-temp-then-replace, never write
the real path directly.
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Progress:
    task: str
    steps_completed: list[str] = field(default_factory=list)
    steps_remaining: list[str] = field(default_factory=list)
    last_tool_result: str | None = None


def load(path: Path) -> Progress | None:
    if not path.exists():
        return None
    # TODO: json.loads(path.read_text(encoding="utf-8")) -> Progress(**data)
    raise NotImplementedError


def save_atomic(path: Path, progress: Progress) -> None:
    # TODO: write to a NamedTemporaryFile in the same directory as `path`
    #       (same volume matters for atomicity), then os.replace(tmp, path).
    #       Wrap the replace in a retry loop for PermissionError — a prior
    #       killed run may still hold a lock on Windows.
    raise NotImplementedError
