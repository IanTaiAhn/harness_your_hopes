"""Runs fresh every invocation -- no in-memory state survives between
runs. Reads feature_list.json + git log FIRST, picks ONE unfinished
feature, implements + tests + commits it, then exits.

Reuses Project 1's tool-loop pattern (read_file/write_file, scoped to
target/ instead of the whole filesystem) and Project 4's evaluator
(pytest, not the model's own self-report) as the commit trigger.

Ablation switches for the Project 5 "Measure" step -- each removes one
component of the harness without touching the code path around it:
    ABLATE_NO_FEATURE_LIST=1  -- agent must infer progress from git log alone
    ABLATE_NO_GITLOG=1        -- agent only has feature_list.json
    ABLATE_NO_COMMIT=1        -- verified work is never committed

Run (from this directory): uv run python coding_agent.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.ollama_client import ChatResult, chat, log_token_usage  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "04-generator-evaluator"))
from evaluator import evaluate_deterministic  # noqa: E402

from contract import CLI_CONTRACT, FEATURES, TEST_FILES  # noqa: E402

MODEL = os.environ.get("HARNESS_MODEL", "qwen3.5:4b")
MAX_TURNS = 15
MAX_RETRIES = 2  # retries-with-feedback within one session, before giving up

HERE = Path(__file__).parent
TARGET = HERE / "target"
TESTS_DIR = TARGET / "tests"

ABLATE_NO_FEATURE_LIST = os.environ.get("ABLATE_NO_FEATURE_LIST") == "1"
ABLATE_NO_GITLOG = os.environ.get("ABLATE_NO_GITLOG") == "1"
ABLATE_NO_COMMIT = os.environ.get("ABLATE_NO_COMMIT") == "1"

# Reference todo.py matching contract.py's CLI_CONTRACT exactly, used only
# when HARNESS_DRY_RUN=1 stands in for a real model with a scripted
# write_file + TASK_COMPLETE response. This exists to validate the loop
# itself (initializer -> N sessions -> evaluator -> commit gate -> feature
# list update) end-to-end without Ollama, not to simulate realistic model
# behavior -- see measure.py.
_REFERENCE_TODO_PY = '''\
import argparse
import json
from pathlib import Path


def _load(store):
    path = Path(store)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save(store, items):
    path = Path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("arg", nargs="?")
    parser.add_argument("--store", required=True)
    parser.add_argument("--pending", action="store_true")
    args = parser.parse_args()

    items = _load(args.store)

    if args.command == "add":
        new_id = 1 if not items else max(i["id"] for i in items) + 1
        items.append({"id": new_id, "text": args.arg, "done": False})
        print(f"Added #{new_id}: {args.arg}")
        _save(args.store, items)
    elif args.command == "list":
        shown = [i for i in items if not (args.pending and i["done"])]
        if not shown:
            print("No items.")
        for i in shown:
            mark = "x" if i["done"] else " "
            print(f"#{i['id']} [{mark}] {i['text']}")
    elif args.command == "done":
        item_id = int(args.arg)
        for i in items:
            if i["id"] == item_id:
                i["done"] = True
                print(f"Done #{item_id}")
                _save(args.store, items)
                return
        print(f"No item with id {item_id}")
    elif args.command == "remove":
        item_id = int(args.arg)
        for i in items:
            if i["id"] == item_id:
                items.remove(i)
                print(f"Removed #{item_id}")
                _save(args.store, items)
                return
        print(f"No item with id {item_id}")


if __name__ == "__main__":
    main()
'''


def _dry_run_chat():
    """Scripted stand-in for chat(): every session gets a write_file call
    with the full reference solution, then a TASK_COMPLETE. Deliberately
    front-loads everything (a real model wouldn't) -- the point is to
    exercise the harness's control flow, not to model realistic behavior.
    """
    state = {"n": 0}

    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        state["n"] += 1
        if state["n"] % 2 == 1:
            return ChatResult(
                message={
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "write_file",
                                "arguments": {"path": "todo.py", "content": _REFERENCE_TODO_PY},
                            }
                        }
                    ],
                },
                prompt_tokens=10,
                completion_tokens=10,
            )
        return ChatResult(
            message={"role": "assistant", "content": "TASK_COMPLETE: wrote todo.py."},
            prompt_tokens=5,
            completion_tokens=5,
        )

    return fake_chat


if os.environ.get("HARNESS_DRY_RUN") == "1":
    chat = _dry_run_chat()
    log_token_usage = lambda *a, **kw: None  # noqa: E731

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the target repo and return its contents.",
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
            "description": (
                "Write UTF-8 text to a file inside the target repo, overwriting it "
                "if it exists. Creates parent directories as needed."
            ),
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
]


def _resolve_in_target(path: str) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (TARGET / candidate).resolve()
    if not resolved.is_relative_to(TARGET.resolve()):
        raise PermissionError(f"{path} resolves outside the target directory")
    return resolved


def read_file(path: str) -> str:
    resolved = _resolve_in_target(path)
    if not resolved.is_file():
        raise FileNotFoundError(f"{path} -> {resolved} does not exist")
    return resolved.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    resolved = _resolve_in_target(path)
    # feature_list.json and tests/ are the harness's own bookkeeping and
    # ground truth -- letting the model touch either would let it mark
    # its own homework, which is exactly the self-reported-"done"
    # failure mode this whole project ladder exists to catch.
    if resolved == TARGET / "feature_list.json":
        raise PermissionError("feature_list.json is managed by the harness, not the model")
    if resolved == TESTS_DIR or TESTS_DIR in resolved.parents:
        raise PermissionError("tests/ is managed by the harness, not the model")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {resolved}"


DISPATCH = {"read_file": read_file, "write_file": write_file}


def _parse_self_report(content: str) -> bool:
    """TASK_COMPLETE -> True. Anything else -- TASK_FAILED, an unlabelled
    final answer, silence -- is treated as False, and is never what
    triggers a commit either way; see evaluate() below.
    """
    return content.strip().upper().startswith("TASK_COMPLETE")


def read_git_log() -> str:
    if ABLATE_NO_GITLOG:
        return "(git log withheld for this ablation run)"
    result = subprocess.run(
        ["git", "log", "--oneline"], cwd=TARGET, capture_output=True, text=True, check=True
    )
    return result.stdout


def load_feature_list() -> dict[str, bool] | None:
    if ABLATE_NO_FEATURE_LIST:
        return None
    path = TARGET / "feature_list.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def pick_target_feature(feature_list: dict[str, bool]) -> str | None:
    for name, _ in FEATURES:
        if not feature_list.get(name, False):
            return name
    return None


def restore_tests_from_git() -> None:
    """The model can technically still write into tests/ if the guard in
    write_file() above has a bug -- this is the second, independent
    guarantee that grading always runs the harness's own tests, never a
    version the agent edited.
    """
    subprocess.run(
        ["git", "checkout", "HEAD", "--", "tests"], cwd=TARGET, capture_output=True
    )


def run_all_tests() -> dict[str, bool]:
    return {
        name: evaluate_deterministic(TESTS_DIR / filename).passed
        for name, filename in TEST_FILES.items()
    }


def build_system_prompt(target_feature: str | None, git_log: str) -> str:
    header = (
        "You are a coding agent building a small CLI to-do app, one "
        "feature per session -- you have zero memory of any prior "
        "session. The whole spec lives in one file, todo.py, built up "
        "incrementally across sessions -- use read_file to check what "
        "already exists before writing anything; do not assume todo.py "
        "is empty. This is a Windows target: the init script is "
        "init.ps1, not init.sh.\n\n"
        f"{CLI_CONTRACT}\n"
        "Git history so far (this is your only memory of prior sessions):\n"
        f"{git_log.strip() or '(no commits yet)'}\n"
    )
    if target_feature is not None:
        _, desc = next(f for f in FEATURES if f[0] == target_feature)
        focus = (
            f"\nYour ONLY job this session: implement {desc}. Implement "
            "exactly this one command and nothing else -- do not "
            "implement other commands from the spec even if they look "
            "easy, and do not touch feature_list.json or anything under "
            "tests/ (those are managed by the harness, not you)."
        )
    else:
        catalog = "\n".join(f"- {name}: {desc}" for name, desc in FEATURES)
        focus = (
            "\nThere is no feature-tracking file this session -- read "
            "the git log above and read todo.py yourself to work out "
            "which of the commands below are already implemented, then "
            "implement exactly ONE that is not, in this order:\n"
            f"{catalog}\n\nDo not touch anything under tests/."
        )
    footer = (
        "\nWhen you are completely done, reply with plain text (no tool "
        "call) starting with exactly one of TASK_COMPLETE or TASK_FAILED, "
        "followed by one short sentence."
    )
    return header + focus + footer


def run_session(system_prompt: str, feedback: str | None = None) -> tuple[str, bool]:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Begin."},
    ]
    if feedback:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Your previous attempt this session was rejected by the "
                    f"test suite: {feedback}\nFix it and try again."
                ),
            }
        )

    log_path = HERE / "measurements" / "tokens.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    for turn in range(MAX_TURNS):
        result = chat(MODEL, messages, tools=TOOLS_SCHEMA)
        log_token_usage(log_path, turn, result)
        message = result.message
        messages.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            content = message.get("content") or ""
            return content, _parse_self_report(content)

        for call in tool_calls:
            fn = call["function"]
            name = fn["name"]
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            try:
                output = DISPATCH[name](**args)
            except Exception as e:  # tool failure is fed back, not fatal
                output = f"error: {e}"
            messages.append({"role": "tool", "content": str(output)})

    return "max turns exceeded without a final answer", False


def commit_target(message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=TARGET, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=TARGET, check=True)


def main() -> None:
    if not (TARGET / ".git").is_dir():
        raise SystemExit(f"{TARGET} is not initialized -- run initializer.py first.")

    feature_list = load_feature_list()
    target_feature = pick_target_feature(feature_list) if feature_list is not None else None

    if feature_list is not None and target_feature is None:
        print("All features complete.")
        return

    mode = "single" if feature_list is not None else "catalog"
    print(f"[session] mode={mode} target={target_feature or '(agent must infer)'}", flush=True)

    system_prompt = build_system_prompt(target_feature, read_git_log())
    before = run_all_tests() if mode == "catalog" else None

    feedback = None
    self_reported = False
    verified = False
    newly_passing: list[str] = []
    for attempt in range(MAX_RETRIES + 1):
        _, self_reported = run_session(system_prompt, feedback=feedback)
        restore_tests_from_git()

        if mode == "single":
            result = evaluate_deterministic(TESTS_DIR / TEST_FILES[target_feature])
            verified = result.passed
            feedback = result.feedback
            newly_passing = [target_feature] if verified else []
        else:
            after = run_all_tests()
            newly_passing = [name for name in TEST_FILES if after[name] and not before[name]]
            verified = bool(newly_passing)
            feedback = (
                "no previously-failing test newly passed -- check git log and "
                "todo.py for what's already implemented, then pick a "
                "different, still-unimplemented command"
            )

        print(
            f"[session] attempt={attempt} self_reported={self_reported} verified={verified}",
            flush=True,
        )
        if verified:
            break

    if not verified:
        print(
            "[session] exhausted retries without a verified pass -- "
            "leaving state for the next fresh process.",
            flush=True,
        )
        return

    if feature_list is not None:
        for name in newly_passing:
            feature_list[name] = True
        (TARGET / "feature_list.json").write_text(
            json.dumps(feature_list, indent=2), encoding="utf-8"
        )

    if ABLATE_NO_COMMIT:
        print(
            f"[session] verified {newly_passing} but commit is ablated -- "
            "leaving changes uncommitted.",
            flush=True,
        )
        return

    commit_target(f"Implement: {', '.join(newly_passing)}")
    print(f"[session] committed: {', '.join(newly_passing)}", flush=True)


if __name__ == "__main__":
    main()
