import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Project 1 also has a tools.py; evict any stale sys.modules cache entry
# so this always resolves to this project's own version regardless of
# which project's test suite happened to import "tools" first in a
# shared pytest process.
sys.modules.pop("tools", None)
import pytest  # noqa: E402
import tools  # noqa: E402


def test_list_dir_lists_names_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("2", encoding="utf-8")
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    (tmp_path / "sub").mkdir()

    assert tools.list_dir(str(tmp_path)) == "a.txt\nb.txt\nsub"


def test_list_dir_empty(tmp_path):
    assert tools.list_dir(str(tmp_path)) == "(empty)"


def test_list_dir_rejects_non_directory(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        tools.list_dir(str(f))


def test_move_file_relocates_and_creates_parents(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hi", encoding="utf-8")
    dest = tmp_path / "by-ext" / "txt" / "a.txt"

    tools.move_file(str(src), str(dest))

    assert not src.exists()
    assert dest.read_text(encoding="utf-8") == "hi"


def test_delete_file_removes_it(tmp_path):
    f = tmp_path / "gone.txt"
    f.write_text("x", encoding="utf-8")

    tools.delete_file(str(f))

    assert not f.exists()


def test_delete_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        tools.delete_file(str(tmp_path / "nope.txt"))


def test_project1_tools_are_reused_not_duplicated():
    # read_file/write_file must come from Project 1's tools.py, not a
    # reimplementation -- this guards against the sys.modules name
    # collision this file's tools.py works around (see its top comment).
    assert tools.read_file.__module__ == "project1_tools"
    assert tools.write_file.__module__ == "project1_tools"
