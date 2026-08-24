"""Thin wrapper around the local Ollama OpenAI-compatible endpoint.

Shared by every project in the ladder so num_ctx handling and token
logging live in one place instead of being copy-pasted per project.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

BASE_URL = "http://localhost:11434/v1"
DEFAULT_NUM_CTX = 8192


@dataclass
class ChatResult:
    message: dict
    prompt_tokens: int
    completion_tokens: int
    raw: dict = field(repr=False, default_factory=dict)


def chat(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    num_ctx: int = DEFAULT_NUM_CTX,
    timeout: int = 300,
) -> ChatResult:
    """Send one chat turn. Raises requests.HTTPError on non-2xx.

    TODO: implement the POST to {BASE_URL}/chat/completions with
    `options: {"num_ctx": num_ctx}` in the Ollama-native fields, parse
    tool_calls out of the response, and populate ChatResult.
    """
    raise NotImplementedError


def log_token_usage(log_path: Path, turn: int, result: ChatResult) -> None:
    """Append a line of token accounting so num_ctx ceilings are visible.

    Do this every turn from day one of Project 1 — Project 2.5 depends
    on having real numbers to look back at, not estimates.
    """
    entry = {
        "turn": turn,
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
