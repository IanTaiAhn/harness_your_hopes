"""Thin wrapper around the local Ollama OpenAI-compatible endpoint.

Shared by every project in the ladder so num_ctx handling and token
logging live in one place instead of being copy-pasted per project.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

# Native Ollama API, not the /v1 OpenAI-compat shim: the native /api/chat
# endpoint is what actually accepts `options.num_ctx` and returns
# prompt_eval_count/eval_count, which is what log_token_usage needs.
BASE_URL = "http://localhost:11434"
DEFAULT_NUM_CTX = 8192


def is_available(models: list[str] | None = None, timeout: int = 3) -> tuple[bool, str]:
    """Cheap preflight check for measure.py scripts: is Ollama reachable,
    and (if given) does `ollama list` actually have the models a
    measurement run needs? Returns (ok, message) rather than raising, so
    callers can print one clear line and exit instead of a raw traceback
    from deep inside a 40-trial loop.
    """
    try:
        response = requests.get(f"{BASE_URL}/api/tags", timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return False, f"Ollama not reachable at {BASE_URL}: {e}"

    if not models:
        return True, "Ollama reachable"

    available = {m["name"] for m in response.json().get("models", [])}
    missing = [
        m for m in models if m not in available and not any(a.startswith(m + ":") for a in available)
    ]
    if missing:
        return False, f"Ollama reachable but missing model(s): {missing} (have: {sorted(available)})"
    return True, "Ollama reachable, all required models present"


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
    """Send one chat turn. Raises requests.HTTPError on non-2xx."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_ctx": num_ctx},
    }
    if tools:
        payload["tools"] = tools

    response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    return ChatResult(
        message=data["message"],
        prompt_tokens=data.get("prompt_eval_count", 0),
        completion_tokens=data.get("eval_count", 0),
        raw=data,
    )


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
