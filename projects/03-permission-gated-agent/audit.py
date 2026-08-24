"""Append-only audit log — every attempted action, allowed or refused."""
from __future__ import annotations

import json
import time
from pathlib import Path


def record(log_path: Path, action: str, path: str, allowed: bool, reason: str = "") -> None:
    entry = {
        "ts": time.time(),
        "action": action,
        "path": path,
        "allowed": allowed,
        "reason": reason,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
