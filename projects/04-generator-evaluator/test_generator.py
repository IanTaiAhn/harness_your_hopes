import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Every project reuses bare module names ("generator" is unique so far,
# but stay consistent with the eviction pattern the other projects use).
sys.modules.pop("generator", None)
import generator  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402


def make_fake_chat(responses):
    """responses: list of ChatResult, consumed one per call."""
    queue = list(responses)

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return queue.pop(0)

    return fake_chat


def silence_logging(monkeypatch):
    monkeypatch.setattr(generator, "log_token_usage", lambda *a, **kw: None)


def tool_call(name, arguments):
    return ChatResult(
        message={"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]},
        prompt_tokens=1,
        completion_tokens=1,
    )


def final(text):
    return ChatResult(message={"role": "assistant", "content": text}, prompt_tokens=1, completion_tokens=1)


def test_writes_file_then_self_reports_complete(tmp_path, monkeypatch):
    out = tmp_path / "solution.py"
    responses = [
        tool_call("write_file", {"path": str(out), "content": "def f(): return 1\n"}),
        final("TASK_COMPLETE: wrote the function."),
    ]
    monkeypatch.setattr(generator, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    solution, self_reported = generator.generate("write f()")

    assert out.read_text(encoding="utf-8") == "def f(): return 1\n"
    assert self_reported is True
    assert solution.startswith("TASK_COMPLETE")


def test_self_reported_failure_is_parsed_false(monkeypatch):
    responses = [final("TASK_FAILED: couldn't handle the edge case.")]
    monkeypatch.setattr(generator, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    _, self_reported = generator.generate("do something hard")

    assert self_reported is False


def test_unlabelled_final_answer_is_not_treated_as_success(monkeypatch):
    # A plain final answer with no TASK_COMPLETE/TASK_FAILED token is not
    # a success claim -- self-report defaults to False, not True.
    responses = [final("I think that should work now.")]
    monkeypatch.setattr(generator, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    _, self_reported = generator.generate("do something")

    assert self_reported is False


def test_feedback_from_a_prior_rejection_reaches_the_model(monkeypatch):
    captured = {}

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        captured["messages"] = messages
        return final("TASK_COMPLETE: fixed it.")

    monkeypatch.setattr(generator, "chat", fake_chat)
    silence_logging(monkeypatch)

    generator.generate("fix the bug", feedback="test_foo failed: assert 1 == 2")

    joined = " ".join(m["content"] for m in captured["messages"] if m.get("content"))
    assert "test_foo failed: assert 1 == 2" in joined


def test_hits_max_turns_without_a_final_answer(tmp_path, monkeypatch):
    target = tmp_path / "x.py"

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return tool_call("write_file", {"path": str(target), "content": "x"})

    monkeypatch.setattr(generator, "chat", fake_chat)
    monkeypatch.setattr(generator, "MAX_TURNS", 2)
    silence_logging(monkeypatch)

    _, self_reported = generator.generate("loop forever")

    assert self_reported is False
