import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Project 3 also has a tools.py sharing this bare module name; evict any
# stale sys.modules entry so this always resolves to this project's own
# version in a shared pytest process.
sys.modules.pop("tools", None)
import tools  # noqa: E402

import pytest


def test_read_file_roundtrip(tmp_path):
    f = tmp_path / "in.txt"
    f.write_text("hello\n", encoding="utf-8")
    assert tools.read_file(str(f)) == "hello\n"


def test_read_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        tools.read_file(str(tmp_path / "nope.txt"))


def test_write_file_creates_parents(tmp_path):
    target = tmp_path / "nested" / "out.txt"
    result = tools.write_file(str(target), "3")
    assert target.read_text(encoding="utf-8") == "3"
    assert "wrote 1 chars" in result


def test_write_file_overwrites(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("old", encoding="utf-8")
    tools.write_file(str(f), "new")
    assert f.read_text(encoding="utf-8") == "new"


def test_run_command_invokes_powershell_without_shell(monkeypatch):
    captured = {}

    def fake_run(args, shell, capture_output, text, timeout):
        captured["args"] = args
        captured["shell"] = shell
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(args, returncode=0, stdout="ok\n", stderr="")

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    output = tools.run_command("Get-ChildItem")

    assert captured["shell"] is False
    assert captured["args"][0] == "powershell"
    assert "Get-ChildItem" in captured["args"]
    assert output == "ok\n"


def test_run_command_appends_stderr_and_exit_code(monkeypatch):
    def fake_run(args, shell, capture_output, text, timeout):
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="boom")

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    output = tools.run_command("Remove-Item nope")

    assert "boom" in output
    assert "exit code 1" in output
