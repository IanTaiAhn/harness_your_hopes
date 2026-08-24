"""Tool implementations + schemas for Project 1.

Keep this the single source of truth for what the model is allowed to
do — agent.py should only import from here, never define ad-hoc tools.
"""
from __future__ import annotations

import subprocess
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
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} -> {resolved} does not exist")
    return resolved.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {resolved}"


def run_command(command: str) -> str:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        shell=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout
    if result.stderr:
        output += f"\n[stderr]\n{result.stderr}"
    if result.returncode != 0:
        output += f"\n[exit code {result.returncode}]"
    return output


DISPATCH = {
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
}
