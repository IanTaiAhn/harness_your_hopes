"""Tool implementations for Project 3.

Reuses read_file/write_file from Project 1 and adds list_dir/move_file/
delete_file, since "organize a messy folder" needs more than read+write.

run_command is deliberately left out of this project's tool set: it's
the one Project 1/2 tool a path-based allowlist structurally can't
police -- there's no single `path` argument to check in an arbitrary
PowerShell command string, so gating it at this layer would be a false
sense of security. See README: that's exactly why the container/sandbox
boundary has to do the real work.
"""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

# Project 1's module is also named `tools` -- a plain `sys.path.insert` +
# `import tools` here would collide with this very module in sys.modules
# (Python caches imports by name, not by path) and fail with a circular-
# import error. Loading it explicitly under a distinct name sidesteps that.
_project1_tools_path = Path(__file__).resolve().parents[1] / "01-bare-metal-loop" / "tools.py"
_spec = importlib.util.spec_from_file_location("project1_tools", _project1_tools_path)
_project1_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_project1_tools)
read_file = _project1_tools.read_file
write_file = _project1_tools.write_file

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write UTF-8 text to a file, overwriting it if it exists.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List the names of files and directories directly inside a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move or rename a file from src to dest.",
            "parameters": {
                "type": "object",
                "properties": {
                    "src": {"type": "string"},
                    "dest": {"type": "string"},
                },
                "required": ["src", "dest"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Permanently delete a file. Destructive -- requires confirmation.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
]


def list_dir(path: str) -> str:
    resolved = Path(path)
    if not resolved.is_dir():
        raise NotADirectoryError(f"{path} -> {resolved} is not a directory")
    entries = sorted(p.name for p in resolved.iterdir())
    return "\n".join(entries) if entries else "(empty)"


def move_file(src: str, dest: str) -> str:
    src_path, dest_path = Path(src), Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_path), str(dest_path))
    return f"moved {src_path} -> {dest_path}"


def delete_file(path: str) -> str:
    resolved = Path(path)
    resolved.unlink()
    return f"deleted {resolved}"


DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "list_dir": list_dir,
    "move_file": move_file,
    "delete_file": delete_file,
}

# Which argument name(s) on each tool are paths the allowlist must check,
# and the default audit/confirmation action label for that tool.
# write_file's label is refined to "overwrite" at call time only when the
# target already exists (see agent.gated_call) -- creating a brand-new
# file isn't a destructive action, clobbering one is.
TOOL_ACTIONS: dict[str, tuple[str, list[str]]] = {
    "read_file": ("read", ["path"]),
    "write_file": ("write", ["path"]),
    "list_dir": ("read", ["path"]),
    # Both ends of a move must be checked -- an agent that could move a
    # file to an unchecked destination could exfiltrate data just as
    # easily as one that could read outside the allowlist directly.
    "move_file": ("move", ["src", "dest"]),
    "delete_file": ("delete", ["path"]),
}
