import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.modules.pop("run_suite", None)
import run_suite  # noqa: E402
from evaluator import EvalResult  # noqa: E402


def test_run_one_succeeds_on_first_attempt(monkeypatch):
    monkeypatch.setattr(run_suite, "generate", lambda task, feedback=None: ("code", True))
    monkeypatch.setattr(run_suite, "evaluate_deterministic", lambda test_path: EvalResult(True, "all tests passed"))

    result = run_suite.run_one({"id": "t1", "prompt": "do it", "test_file": "test_t1.py"})

    assert result == {"task": "t1", "attempt": 0, "self_reported": True, "verified": True}


def test_run_one_catches_a_false_done_claim_and_recovers_on_retry(monkeypatch):
    # Attempt 0: generator claims success but the evaluator rejects it.
    # Attempt 1: feedback-driven retry actually passes. This is the
    # project's "done when" case -- self-report says yes, evaluator says
    # no, then retry-with-feedback succeeds.
    generate_calls = []

    def fake_generate(task, feedback=None):
        generate_calls.append(feedback)
        return "code", True  # self-reports success both times

    eval_results = iter([EvalResult(False, "test_t1 failed: assert 1 == 2"), EvalResult(True, "all tests passed")])
    monkeypatch.setattr(run_suite, "generate", fake_generate)
    monkeypatch.setattr(run_suite, "evaluate_deterministic", lambda test_path: next(eval_results))

    result = run_suite.run_one({"id": "t1", "prompt": "do it", "test_file": "test_t1.py"})

    assert result == {"task": "t1", "attempt": 1, "self_reported": True, "verified": True}
    assert generate_calls == [None, "test_t1 failed: assert 1 == 2"]


def test_run_one_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(run_suite, "generate", lambda task, feedback=None: ("code", True))
    monkeypatch.setattr(run_suite, "evaluate_deterministic", lambda test_path: EvalResult(False, "still failing"))

    result = run_suite.run_one({"id": "t1", "prompt": "do it", "test_file": "test_t1.py"})

    assert result == {"task": "t1", "attempt": run_suite.MAX_RETRIES, "self_reported": True, "verified": False}


def test_main_computes_the_self_reported_vs_verified_gap(tmp_path, monkeypatch):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    (tasks_dir / "a.json").write_text('{"id": "a", "prompt": "p", "test_file": "test_a.py"}', encoding="utf-8")
    (tasks_dir / "b.json").write_text('{"id": "b", "prompt": "p", "test_file": "test_b.py"}', encoding="utf-8")

    monkeypatch.setattr(run_suite, "TASKS_DIR", tasks_dir)
    monkeypatch.setattr(run_suite, "LOG_PATH", tmp_path / "runs.jsonl")

    # "a" self-reports success but never actually passes (the gap this
    # whole project measures); "b" is honestly correct both ways.
    def fake_run_one(task_spec):
        if task_spec["id"] == "a":
            return {"task": "a", "attempt": run_suite.MAX_RETRIES, "self_reported": True, "verified": False}
        return {"task": "b", "attempt": 0, "self_reported": True, "verified": True}

    monkeypatch.setattr(run_suite, "run_one", fake_run_one)

    run_suite.main()

    lines = (tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
