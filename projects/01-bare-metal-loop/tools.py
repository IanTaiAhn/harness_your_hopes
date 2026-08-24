"""Tool implementations + schemas for Project 1.

Keep this the single source of truth for what the model is allowed to
do — agent.py should only import from here, never define ad-hoc tools.
"""
from __future__ import annotations

from pathlib import Path

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
            "name": "run_command",
            "description": (
                "Run a Windows PowerShell command. Do NOT use Unix commands "
                "(ls, cat, rm) — use Get-ChildItem, Get-Content, Remove-Item."
            ),
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]


def read_file(path: str) -> str:
    # TODO: Path(path).resolve(), read_text(encoding="utf-8"), sane error on missing file
    raise NotImplementedError


def write_file(path: str, content: str) -> str:
    # TODO: Path(path).resolve(), write_text(encoding="utf-8"), return a confirmation string
    raise NotImplementedError


def run_command(command: str) -> str:
    # TODO: subprocess.run(["powershell", "-Command", command], shell=False,
    #       capture_output=True, text=True, timeout=30); return combined stdout/stderr
    raise NotImplementedError


DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
}
