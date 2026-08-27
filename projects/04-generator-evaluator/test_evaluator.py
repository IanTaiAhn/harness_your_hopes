import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.modules.pop("evaluator", None)
import evaluator  # noqa: E402
from common.ollama_client import ChatResult  # noqa: E402


def _write_test(tmp_path, body):
    test_path = tmp_path / "test_sample.py"
    test_path.write_text(body, encoding="utf-8")
    return test_path


def test_passing_test_reports_passed(tmp_path):
    test_path = _write_test(tmp_path, "def test_ok():\n    assert 1 == 1\n")

    result = evaluator.evaluate_deterministic(test_path)

    assert result.passed is True
    assert result.feedback == "all tests passed"


def test_failing_test_reports_specific_feedback_not_just_failed(tmp_path):
    test_path = _write_test(
        tmp_path,
        "def test_bad():\n    assert 1 == 2, 'one is not two'\n",
    )

    result = evaluator.evaluate_deterministic(test_path)

    assert result.passed is False
    assert "test_bad" in result.feedback
    assert result.feedback != "failed"


def test_evaluate_against_a_real_ground_truth_check_directly_by_path():
    # This is the same call evaluator.py makes against tasks/test_task_*.py
    # -- confirms collect_ignore_glob in tasks/conftest.py (which excludes
    # these from a repo-wide `pytest` run) does not stop a direct,
    # explicit-path run from executing and reporting real pass/fail.
    task_dir = Path(__file__).parent / "tasks"
    result = evaluator.evaluate_deterministic(task_dir / "test_task_01.py")

    # No solution has been generated in this test environment, so the
    # check must fail loudly, not be silently skipped (a skip would read
    # as returncode 0, which evaluate_deterministic would wrongly report
    # as passed).
    assert result.passed is False
    assert "did not write" in result.feedback or "task_01_fizzbuzz" in result.feedback


def test_timeout_is_reported_as_failure(tmp_path, monkeypatch):
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="pytest", timeout=60)

    monkeypatch.setattr(evaluator.subprocess, "run", fake_run)
    test_path = _write_test(tmp_path, "def test_ok():\n    assert True\n")

    result = evaluator.evaluate_deterministic(test_path)

    assert result.passed is False
    assert "timed out" in result.feedback


def test_judge_parses_pass_response(monkeypatch):
    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return ChatResult(
            message={"role": "assistant", "content": "PASS: explanation is clear and correct."},
            prompt_tokens=1,
            completion_tokens=1,
        )

    monkeypatch.setattr("common.ollama_client.chat", fake_chat)

    result = evaluator.evaluate_judge("explain recursion", "a summary")

    assert result.passed is True
    assert "clear" in result.feedback


def test_judge_parses_fail_response(monkeypatch):
    def fake_chat(model, messages, tools=None, num_ctx=8192, timeout=300):
        return ChatResult(
            message={"role": "assistant", "content": "FAIL: missing the base case."},
            prompt_tokens=1,
            completion_tokens=1,
        )

    monkeypatch.setattr("common.ollama_client.chat", fake_chat)

    result = evaluator.evaluate_judge("explain recursion", "a summary")

    assert result.passed is False
    assert "base case" in result.feedback
