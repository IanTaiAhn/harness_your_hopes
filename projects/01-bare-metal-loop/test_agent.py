import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Project 3 also has an agent.py/tools.py sharing these bare module
# names; evict any stale sys.modules entry so this always resolves to
# this project's own version in a shared pytest process.
sys.modules.pop("agent", None)
sys.modules.pop("tools", None)
import agent  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402


def make_fake_chat(responses):
    """responses: list of ChatResult, consumed one per call."""
    queue = list(responses)

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return queue.pop(0)

    return fake_chat


def silence_logging(monkeypatch):
    monkeypatch.setattr(agent, "log_token_usage", lambda *a, **kw: None)


def test_happy_path_reads_then_writes_then_finishes(tmp_path, monkeypatch):
    src = tmp_path / "input.txt"
    src.write_text("a\nb\nc\n", encoding="utf-8")
    out = tmp_path / "output.txt"

    responses = [
        ChatResult(
            message={
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": str(src)}}}
                ],
            },
            prompt_tokens=10,
            completion_tokens=5,
        ),
        ChatResult(
            message={
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "write_file",
                            "arguments": {"path": str(out), "content": "3"},
                        }
                    }
                ],
            },
            prompt_tokens=20,
            completion_tokens=5,
        ),
        ChatResult(
            message={"role": "assistant", "content": "Done."},
            prompt_tokens=25,
            completion_tokens=3,
        ),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    assert agent.run("count lines") is True
    assert out.read_text(encoding="utf-8") == "3"


def test_malformed_tool_json_retries_then_recovers(tmp_path, monkeypatch):
    out = tmp_path / "output.txt"

    responses = [
        ChatResult(
            message={"role": "assistant", "content": '{"name": "write_file", "arguments": {'},
            prompt_tokens=1,
            completion_tokens=1,
        ),
        ChatResult(
            message={
                "role": "assistant",
                "content": json.dumps(
                    {"name": "write_file", "arguments": {"path": str(out), "content": "ok"}}
                ),
            },
            prompt_tokens=1,
            completion_tokens=1,
        ),
        ChatResult(
            message={"role": "assistant", "content": "Done."},
            prompt_tokens=1,
            completion_tokens=1,
        ),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    assert agent.run("write ok to file") is True
    assert out.read_text(encoding="utf-8") == "ok"


def test_exceeding_max_json_retries_fails(monkeypatch):
    malformed = ChatResult(
        message={"role": "assistant", "content": '{"name": "write_file", "arguments": {'},
        prompt_tokens=1,
        completion_tokens=1,
    )
    # MAX_JSON_RETRIES + 1 malformed responses in a row exceeds the budget
    responses = [malformed] * (agent.MAX_JSON_RETRIES + 1)
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    assert agent.run("write ok to file") is False


def test_retry_budget_ablation_zero_fails_on_first_malformed_reply(monkeypatch):
    malformed = ChatResult(
        message={"role": "assistant", "content": '{"name": "write_file", "arguments": {'},
        prompt_tokens=1,
        completion_tokens=1,
    )
    monkeypatch.setattr(agent, "chat", make_fake_chat([malformed]))
    monkeypatch.setattr(agent, "MAX_JSON_RETRIES", 0)
    silence_logging(monkeypatch)

    assert agent.run("write ok to file") is False


def test_hits_max_turns_without_finishing(monkeypatch):
    # Model keeps calling read_file forever and never gives a final answer.
    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return ChatResult(
            message={
                "role": "assistant",
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": "nope.txt"}}}
                ],
            },
            prompt_tokens=1,
            completion_tokens=1,
        )

    monkeypatch.setattr(agent, "chat", fake_chat)
    monkeypatch.setattr(agent, "MAX_TURNS", 3)
    silence_logging(monkeypatch)

    assert agent.run("count lines") is False
