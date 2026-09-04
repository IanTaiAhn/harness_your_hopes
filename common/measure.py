"""Shared helpers for each project's measure.py script.

Two things every project needs, factored out so they're not
copy-pasted six times: an append-only per-trial JSONL log (the raw data,
kept forever, one line per trial — this is what "understand *why* it
failed" comes from, not just the pass/fail table), and marker-delimited
regeneration of measurements/results.md so a script can rewrite the
tables it owns without clobbering any Takeaway prose a human wrote
around them.

Every results.md keeps its generated tables between
`<!-- MEASURE:BEGIN <key> -->` / `<!-- MEASURE:END <key> -->` pairs.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def fill_marker(text: str, key: str, replacement: str) -> str:
    """Replace everything between the BEGIN key/END key markers with
    `replacement`. Raises if the markers aren't present in `text` — a
    silent no-op would hide a typo'd key instead of failing loudly.
    """
    begin = f"<!-- MEASURE:BEGIN {key} -->"
    end = f"<!-- MEASURE:END {key} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"markers for {key!r} not found in results.md")
    # Replacement passed as a function, not a string: re.sub treats a
    # string replacement's backslashes as regex backreferences (`\1` etc),
    # which corrupts any replacement text containing literal Windows
    # paths like `\\?\C:\...`.
    return pattern.sub(lambda _m: f"{begin}\n{replacement.strip()}\n{end}", text)


def update_results_md(path: Path, sections: dict[str, str]) -> None:
    """sections: {marker_key: new_markdown_between_the_markers}."""
    text = path.read_text(encoding="utf-8")
    for key, replacement in sections.items():
        text = fill_marker(text, key, replacement)
    path.write_text(text, encoding="utf-8")
