"""Structured progress file: read/write with atomic replace.

A half-written JSON file after a hard kill is exactly the failure this
project exists to prevent — always write-temp-then-replace, never write
the real path directly.
"""
from __future__ import annotations

import json
import os
import tempfile
import time
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
    data = json.loads(path.read_text(encoding="utf-8"))
    return Progress(**data)


def save_atomic(path: Path, progress: Progress) -> None:
    """Write `progress` to `path` without ever leaving a half-written file.

    Writes to a temp file in the same directory (same volume, so the
    replace below is atomic), then os.replace()s it onto the real path.
    A prior hard-killed run may still hold a lock on `path` on Windows,
    so the replace itself is retried with backoff rather than raising
    straight away.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".progress-", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(progress), f, indent=2)
        _replace_with_retry(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def _replace_with_retry(
    tmp_path: Path, path: Path, attempts: int = 5, base_delay: float = 0.2
) -> None:
    for attempt in range(attempts):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2**attempt))
