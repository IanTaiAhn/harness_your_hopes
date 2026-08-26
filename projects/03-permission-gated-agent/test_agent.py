import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# Project 1 also has an agent.py/tools.py. A shared pytest process caches
# imports by bare module name (sys.modules), not by path, so whichever
# project's test suite happened to import "agent"/"tools" first would
# silently win here otherwise -- evict any stale entry before importing.
for _name in ("agent", "tools", "policy", "audit"):
    sys.modules.pop(_name, None)
import agent  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402
from policy import Allowlist  # noqa: E402


def make_fake_chat(responses):
    queue = list(responses)

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return queue.pop(0)

    return fake_chat


def isolate(monkeypatch, tmp_path):
    """Point the agent at a throwaway workspace/allowlist/audit log so
    tests never touch the real sandbox/ or measurements/ directories."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(agent, "WORKSPACE_ROOT", str(workspace))
    monkeypatch.setattr(agent, "allowlist", Allowlist([str(workspace)]))
    monkeypatch.setattr(agent, "AUDIT_LOG", tmp_path / "audit.jsonl")
    monkeypatch.setattr(agent, "log_token_usage", lambda *a, **kw: None)
    return workspace


def read_audit(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def tool_call_response(name, arguments):
    return ChatResult(
        message={"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]},
        prompt_tokens=1,
        completion_tokens=1,
    )


def final_answer(text):
    return ChatResult(message={"role": "assistant", "content": text}, prompt_tokens=1, completion_tokens=1)


def test_happy_path_lists_then_moves_then_finishes(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    (workspace / "a.txt").write_text("hi", encoding="utf-8")

    responses = [
        tool_call_response("list_dir", {"path": str(workspace)}),
        tool_call_response(
            "move_file",
            {"src": str(workspace / "a.txt"), "dest": str(workspace / "txt" / "a.txt")},
        ),
        final_answer("Done."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("organize by extension") is True
    assert (workspace / "txt" / "a.txt").read_text(encoding="utf-8") == "hi"

    entries = read_audit(agent.AUDIT_LOG)
    assert [e["action"] for e in entries] == ["read", "move"]
    assert all(e["allowed"] for e in entries)


def test_escape_attempt_is_refused_and_audited(tmp_path, monkeypatch):
    isolate(monkeypatch, tmp_path)
    outside = tmp_path / "secret.txt"
    outside.write_text("nope", encoding="utf-8")

    responses = [
        tool_call_response("read_file", {"path": str(outside)}),
        final_answer("Couldn't read it."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    # The loop still finishes cleanly -- the point is the read is blocked,
    # not that the whole run crashes.
    assert agent.run("read the secret file") is True

    entries = read_audit(agent.AUDIT_LOG)
    assert entries[0]["action"] == "read"
    assert entries[0]["allowed"] is False
    assert "outside allowlist" in entries[0]["reason"]
    assert not outside.read_text(encoding="utf-8") == ""  # untouched, sanity check


def test_delete_without_tty_is_refused_by_default(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    target = workspace / "gone.txt"
    target.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    responses = [
        tool_call_response("delete_file", {"path": str(target)}),
        final_answer("Could not delete."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("delete gone.txt") is True
    assert target.exists()  # refused by default with no interactive confirmation available

    entries = read_audit(agent.AUDIT_LOG)
    assert entries[0]["action"] == "delete"
    assert entries[0]["allowed"] is False
    assert entries[0]["reason"] == "not confirmed"


def test_delete_with_tty_confirmation_proceeds(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    target = workspace / "gone.txt"
    target.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")

    responses = [
        tool_call_response("delete_file", {"path": str(target)}),
        final_answer("Deleted."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("delete gone.txt") is True
    assert not target.exists()


def test_overwrite_of_existing_file_requires_confirmation(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    target = workspace / "existing.txt"
    target.write_text("old", encoding="utf-8")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    responses = [
        tool_call_response("write_file", {"path": str(target), "content": "new"}),
        final_answer("Could not overwrite."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("overwrite existing.txt") is True
    assert target.read_text(encoding="utf-8") == "old"  # refused, unchanged

    entries = read_audit(agent.AUDIT_LOG)
    assert entries[0]["action"] == "overwrite"
    assert entries[0]["allowed"] is False


def test_new_file_write_does_not_require_confirmation(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    target = workspace / "brand_new.txt"
    # If a fresh write were (wrongly) gated as destructive, this would
    # cause it to be refused -- proving it isn't consulted at all.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    responses = [
        tool_call_response("write_file", {"path": str(target), "content": "new"}),
        final_answer("Done."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("write brand_new.txt") is True
    assert target.read_text(encoding="utf-8") == "new"

    entries = read_audit(agent.AUDIT_LOG)
    assert entries[0]["action"] == "write"
    assert entries[0]["allowed"] is True


def test_move_to_destination_outside_allowlist_is_refused(tmp_path, monkeypatch):
    workspace = isolate(monkeypatch, tmp_path)
    src = workspace / "a.txt"
    src.write_text("hi", encoding="utf-8")
    outside_dest = tmp_path / "exfiltrated.txt"

    responses = [
        tool_call_response("move_file", {"src": str(src), "dest": str(outside_dest)}),
        final_answer("Could not move it."),
    ]
    monkeypatch.setattr(agent, "chat", make_fake_chat(responses))

    assert agent.run("move a.txt out") is True
    assert src.exists()  # move never happened
    assert not outside_dest.exists()

    entries = read_audit(agent.AUDIT_LOG)
    assert entries[0]["action"] == "move"
    assert entries[0]["allowed"] is False
