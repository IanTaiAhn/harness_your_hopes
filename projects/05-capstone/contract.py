"""Single source of truth for the target CLI's spec and feature ladder.

Both initializer.py (writes feature_list.json + CONTRACT.md into target/)
and coding_agent.py (builds the coding agent's prompt) import from here,
and the fixed ground-truth tests in tests_template/ were written against
this exact text -- so the spec the model is given and the spec the tests
check can never quietly drift apart from each other.
"""
from __future__ import annotations

# Ordered ladder: coding_agent.py works top to bottom, exactly one entry
# per fresh process. The name is also the feature_list.json key and (via
# TEST_FILES below) the ground-truth test for that entry.
FEATURES: list[tuple[str, str]] = [
    ("add-item", "the `add <text>` command"),
    ("list-items", "the `list` command"),
    ("mark-done", "the `done <id>` command"),
    ("remove-item", "the `remove <id>` command"),
    ("list-pending", "the `list --pending` flag"),
]

# feature name -> the ground-truth test file that verifies it (see
# tests_template/), copied into target/tests/ by initializer.py.
TEST_FILES: dict[str, str] = {
    "add-item": "test_01_add_item.py",
    "list-items": "test_02_list_items.py",
    "mark-done": "test_03_mark_done.py",
    "remove-item": "test_04_remove_item.py",
    "list-pending": "test_05_list_pending.py",
}

CLI_CONTRACT = """\
# todo.py CLI contract

A single file at the repo root, `todo.py`, built up one command per
session. Invoke it (and be invoked, in tests) as:

    uv run python todo.py <command> [args] --store <path>

Storage: a JSON file at the path given by `--store`. Structure: a JSON
list of objects `{"id": int, "text": str, "done": bool}`. Create the
file (and any missing parent directories) on first write. Treat a
missing file as an empty list on read. Never read or write any file
other than the one named by `--store`.

Commands:

- `add <text>` -- append a new item. `id` = 1 if the store is empty,
  else `(max existing id) + 1`. `done` starts `false`. Print exactly:
  `Added #<id>: <text>`
- `list` -- print one line per item, in id order, formatted as
  `#<id> [x] <text>` if done else `#<id> [ ] <text>`. If there are no
  items, print exactly: `No items.`
- `list --pending` -- same as `list` but only items where `done` is
  `false`. Same `No items.` message if none remain.
- `done <id>` -- set that item's `done` to `true`. Print `Done #<id>`
  on success, or `No item with id <id>` if the id doesn't exist.
- `remove <id>` -- delete that item entirely. Print `Removed #<id>` on
  success, or `No item with id <id>` if the id doesn't exist.

Always exit 0. Report problems as plain stdout text, never raise an
uncaught exception -- the test suite checks stdout only, never exit
codes.
"""
