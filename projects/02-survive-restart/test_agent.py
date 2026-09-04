import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "01-bare-metal-loop"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Project 1 also has an agent.py/tools.py sharing these bare module
# names; evict any stale sys.modules entry so this always resolves to
# this project's own version in a shared pytest process.
sys.modules.pop("agent", None)
sys.modules.pop("tools", None)
sys.modules.pop("state", None)
import agent  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402


def make_fake_chat(responses):
    queue = list(responses)

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return queue.pop(0)

    return fake_chat


def silence_logging(monkeypatch):
    monkeypatch.setattr(agent, "log_token_usage", lambda *a, **kw: None)


def tool_call(name, arguments):
    return ChatResult(
        message={"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]},
        prompt_tokens=1,
        completion_tokens=1,
    )


# --- seed_plan_of_length / check_synthetic_summary: the pure-logic pieces
# measure.py's crossover-length comparison depends on. ---


def test_seed_plan_of_length_has_n_plus_one_steps():
    plan = agent.seed_plan_of_length(5)
    assert len(plan) == 6
    assert "MARKER_1_CONTENT" in plan[0]
    assert "MARKER_5_CONTENT" in plan[4]
    assert "file1.txt" in plan[5] and "file5.txt" in plan[5]


def test_seed_plan_dispatches_synthetic_prefix():
    assert agent.seed_plan("synthetic:3") == agent.seed_plan_of_length(3)
    assert agent.seed_plan(agent.DEFAULT_TASK) == agent.DEFAULT_PLAN
    assert agent.seed_plan("something else") == ["something else"]


def test_check_synthetic_summary_requires_every_marker():
    assert agent.check_synthetic_summary("MARKER_1_CONTENT\nMARKER_2_CONTENT", 2) is True
    assert agent.check_synthetic_summary("MARKER_1_CONTENT", 2) is False


def test_build_messages_naive_keeps_only_the_last_n_raw_turns(monkeypatch):
    monkeypatch.setattr(agent, "REPLAY_KEEP_LAST", 2)
    history = [{"role": "user", "content": f"turn{i}"} for i in range(5)]

    messages = agent.build_messages_naive("do the thing", history, "next step")

    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "Overall task: do the thing"}
    assert messages[2:4] == history[-2:]
    assert messages[-1] == {"role": "user", "content": "CURRENT STEP -- do this now: next step"}


# --- KILL_AFTER_TURN / KILL_BEFORE_FIRST_SAVE: confirm they fire at the
# right point without actually terminating the test process. ---


class _KillSignal(Exception):
    pass


def _raise_instead_of_exit(monkeypatch):
    def fake_exit(code):
        raise _KillSignal(code)

    monkeypatch.setattr(agent.os, "_exit", fake_exit)


def test_kill_after_turn_fires_after_that_turns_save(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "PROGRESS_PATH", tmp_path / "progress.json")
    monkeypatch.setattr(agent, "KILL_AFTER_TURN", 0)
    _raise_instead_of_exit(monkeypatch)
    silence_logging(monkeypatch)

    responses = [tool_call("write_file", {"path": str(tmp_path / "file1.txt"), "content": "x"})]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    import pytest

    with pytest.raises(_KillSignal):
        agent.run(agent.DEFAULT_TASK)

    # The turn-0 step's progress must already be on disk -- that's the
    # entire point of saving before the kill point, not after.
    saved = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert saved["steps_completed"] == [agent.DEFAULT_PLAN[0]]


def test_kill_before_first_save_fires_before_any_progress_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "PROGRESS_PATH", tmp_path / "progress.json")
    monkeypatch.setattr(agent, "KILL_BEFORE_FIRST_SAVE", True)
    _raise_instead_of_exit(monkeypatch)
    silence_logging(monkeypatch)

    responses = [tool_call("write_file", {"path": str(tmp_path / "file1.txt"), "content": "x"})]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    import pytest

    with pytest.raises(_KillSignal):
        agent.run(agent.DEFAULT_TASK)

    saved = json.loads((tmp_path / "progress.json").read_text(encoding="utf-8"))
    assert saved["steps_completed"] == []  # the initial seed save, no steps done yet
