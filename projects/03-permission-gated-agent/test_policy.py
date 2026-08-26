import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pytest  # noqa: E402
from policy import Allowlist, PolicyViolation  # noqa: E402


def test_allows_path_inside_root(tmp_path):
    allowlist = Allowlist([str(tmp_path)])
    target = tmp_path / "notes.txt"
    assert allowlist.check(str(target)) == target.resolve()


def test_allows_root_itself(tmp_path):
    allowlist = Allowlist([str(tmp_path)])
    assert allowlist.check(str(tmp_path)) == tmp_path.resolve()


def test_rejects_dotdot_traversal_out_of_root(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("nope", encoding="utf-8")

    allowlist = Allowlist([str(root)])
    with pytest.raises(PolicyViolation):
        allowlist.check(str(root / ".." / "secret.txt"))


def test_rejects_sibling_directory_with_shared_prefix(tmp_path):
    # "workspace-evil" starts with the same characters as "workspace" --
    # a naive string-prefix check would wrongly allow this.
    root = tmp_path / "workspace"
    root.mkdir()
    evil = tmp_path / "workspace-evil"
    evil.mkdir()

    allowlist = Allowlist([str(root)])
    with pytest.raises(PolicyViolation):
        allowlist.check(str(evil / "secret.txt"))


def test_rejects_symlink_escape(tmp_path):
    # Linux analog of a Windows directory junction: a symlink inside the
    # allowlisted root that points outside it. Path.resolve() follows
    # symlinks, so the resolved target -- not the link's own location --
    # is what gets checked.
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "secret"
    outside.mkdir()
    (outside / "data.txt").write_text("nope", encoding="utf-8")

    link = root / "escape"
    link.symlink_to(outside, target_is_directory=True)

    allowlist = Allowlist([str(root)])
    with pytest.raises(PolicyViolation):
        allowlist.check(str(link / "data.txt"))


def test_requires_confirmation_for_delete_and_overwrite():
    allowlist = Allowlist(["/tmp"])
    assert allowlist.requires_confirmation("delete") is True
    assert allowlist.requires_confirmation("overwrite") is True
    assert allowlist.requires_confirmation("read") is False
    assert allowlist.requires_confirmation("write") is False
