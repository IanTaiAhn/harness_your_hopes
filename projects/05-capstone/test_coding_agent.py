"""Mocked unit tests -- no live Ollama in this authoring environment, so
`chat()` is faked exactly like every other project's tests. Git and
pytest are real (subprocess calls against a throwaway target/ built by
initializer.py in tmp_path), since those are cheap, deterministic, and
exercising them for real is the whole point of testing this file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.modules.pop("coding_agent", None)
import coding_agent  # noqa: E402
from contract import FEATURES  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402


def make_fake_chat(responses):
    queue = list(responses)

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return queue.pop(0)

    return fake_chat


def silence_logging(monkeypatch):
    monkeypatch.setattr(coding_agent, "log_token_usage", lambda *a, **kw: None)


def tool_call(name, arguments):
    return ChatResult(
        message={"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}}]},
        prompt_tokens=1,
        completion_tokens=1,
    )


def final(text):
    return ChatResult(message={"role": "assistant", "content": text}, prompt_tokens=1, completion_tokens=1)


ADD_ONLY_TODO_PY = '''\
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("argument", nargs="?")
    parser.add_argument("--store", required=True)
    parser.add_argument("--pending", action="store_true")
    args = parser.parse_args()
    store = Path(args.store)
    items = json.loads(store.read_text(encoding="utf-8")) if store.exists() else []
    if args.command == "add":
        new_id = max((i["id"] for i in items), default=0) + 1
        items.append({"id": new_id, "text": args.argument, "done": False})
        print(f"Added #{new_id}: {args.argument}")
        store.write_text(json.dumps(items), encoding="utf-8")
    elif args.command == "list":
        shown = [i for i in items if not (args.pending and i["done"])]
        if not shown:
            print("No items.")
        else:
            for i in shown:
                print(f"#{i['id']} [{'x' if i['done'] else ' '}] {i['text']}")

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def target(tmp_path, monkeypatch):
    """A real initializer.py-built target/, relocated under tmp_path so
    tests never touch the real projects/05-capstone/target/.
    """
    dest = tmp_path / "target"
    monkeypatch.setattr(coding_agent, "TARGET", dest)
    monkeypatch.setattr(coding_agent, "TESTS_DIR", dest / "tests")

    real_here = Path(__file__).parent
    dest.mkdir()
    feature_list = {name: False for name, _ in FEATURES}
    (dest / "feature_list.json").write_text(json.dumps(feature_list, indent=2), encoding="utf-8")
    import shutil

    shutil.copytree(real_here / "tests_template", dest / "tests")

    subprocess.run(["git", "init"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=dest, check=True, capture_output=True)
    return dest


def test_pick_target_feature_returns_first_unfinished():
    feature_list = {"add-item": True, "list-items": False, "mark-done": False}
    assert coding_agent.pick_target_feature(feature_list) == "list-items"


def test_pick_target_feature_none_when_all_done():
    feature_list = {name: True for name, _ in FEATURES}
    assert coding_agent.pick_target_feature(feature_list) is None


def test_write_file_rejects_path_outside_target(target):
    with pytest.raises(PermissionError):
        coding_agent.write_file(str(target.parent / "escape.txt"), "x")


def test_write_file_rejects_dotdot_traversal(target):
    with pytest.raises(PermissionError):
        coding_agent.write_file("../escape.txt", "x")


def test_write_file_rejects_feature_list_json(target):
    with pytest.raises(PermissionError):
        coding_agent.write_file("feature_list.json", '{"add-item": true}')


def test_write_file_rejects_tests_dir(target):
    with pytest.raises(PermissionError):
        coding_agent.write_file("tests/test_01_add_item.py", "def test_x(): assert False")


def test_write_file_allows_todo_py(target):
    coding_agent.write_file("todo.py", "print('hi')")
    assert (target / "todo.py").read_text(encoding="utf-8") == "print('hi')"


def test_self_report_parsing():
    assert coding_agent._parse_self_report("TASK_COMPLETE: done") is True
    assert coding_agent._parse_self_report("TASK_FAILED: nope") is False
    assert coding_agent._parse_self_report("looks done to me") is False


def test_main_single_mode_happy_path_commits_and_updates_feature_list(target, monkeypatch):
    responses = [
        tool_call("write_file", {"path": "todo.py", "content": ADD_ONLY_TODO_PY}),
        final("TASK_COMPLETE: implemented add."),
    ]
    monkeypatch.setattr(coding_agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    coding_agent.main()

    feature_list = json.loads((target / "feature_list.json").read_text(encoding="utf-8"))
    assert feature_list["add-item"] is True
    assert feature_list["list-items"] is False

    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    assert "add-item" in log


def test_main_evaluator_rejects_false_done_claim_then_retry_succeeds(target, monkeypatch):
    # First attempt: model self-reports TASK_COMPLETE but never actually
    # wrote todo.py -- the evaluator must catch this, not the self-report.
    responses = [
        final("TASK_COMPLETE: trust me, it works."),
        tool_call("write_file", {"path": "todo.py", "content": ADD_ONLY_TODO_PY}),
        final("TASK_COMPLETE: implemented add, for real this time."),
    ]
    monkeypatch.setattr(coding_agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    coding_agent.main()

    feature_list = json.loads((target / "feature_list.json").read_text(encoding="utf-8"))
    assert feature_list["add-item"] is True


def test_main_gives_up_after_max_retries_without_committing(target, monkeypatch):
    monkeypatch.setattr(coding_agent, "MAX_RETRIES", 1)
    responses = [final("TASK_FAILED: stuck.")] * 2
    monkeypatch.setattr(coding_agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    before_log = subprocess.run(
        ["git", "log", "--oneline"], cwd=target, capture_output=True, text=True, check=True
    ).stdout

    coding_agent.main()

    feature_list = json.loads((target / "feature_list.json").read_text(encoding="utf-8"))
    assert feature_list["add-item"] is False
    after_log = subprocess.run(
        ["git", "log", "--oneline"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    assert before_log == after_log


def test_ablate_no_commit_updates_feature_list_but_leaves_git_clean_log(target, monkeypatch):
    monkeypatch.setattr(coding_agent, "ABLATE_NO_COMMIT", True)
    responses = [
        tool_call("write_file", {"path": "todo.py", "content": ADD_ONLY_TODO_PY}),
        final("TASK_COMPLETE: implemented add."),
    ]
    monkeypatch.setattr(coding_agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    coding_agent.main()

    feature_list = json.loads((target / "feature_list.json").read_text(encoding="utf-8"))
    assert feature_list["add-item"] is True

    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    assert "add-item" not in log
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    assert status.strip() != ""  # uncommitted changes left behind


def test_ablate_no_feature_list_falls_back_to_catalog_mode(target, monkeypatch):
    (target / "feature_list.json").unlink()
    monkeypatch.setattr(coding_agent, "ABLATE_NO_FEATURE_LIST", True)
    responses = [
        tool_call("write_file", {"path": "todo.py", "content": ADD_ONLY_TODO_PY}),
        final("TASK_COMPLETE: implemented add."),
    ]
    monkeypatch.setattr(coding_agent, "chat", make_fake_chat(responses))
    silence_logging(monkeypatch)

    coding_agent.main()

    assert not (target / "feature_list.json").exists()
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=target, capture_output=True, text=True, check=True
    ).stdout
    assert "add-item" in log


def test_ablate_no_gitlog_hides_history_from_the_prompt(target, monkeypatch):
    monkeypatch.setattr(coding_agent, "ABLATE_NO_GITLOG", True)
    captured = {}

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        captured["system"] = messages[0]["content"]
        return final("TASK_FAILED: stub.")

    monkeypatch.setattr(coding_agent, "chat", fake_chat)
    silence_logging(monkeypatch)

    coding_agent.main()

    assert "withheld" in captured["system"]


def test_all_features_complete_takes_no_action(target, monkeypatch):
    feature_list = {name: True for name, _ in FEATURES}
    (target / "feature_list.json").write_text(json.dumps(feature_list), encoding="utf-8")

    def fail_if_called(*a, **kw):
        raise AssertionError("chat() should not be called when all features are done")

    monkeypatch.setattr(coding_agent, "chat", fail_if_called)

    coding_agent.main()  # should return early, not raise
