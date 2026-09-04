"""Automates Project 3's Measure step for the attacks that don't require
a specific OS: no mocking, no Ollama — this drives `agent.gated_call()`
(the real allowlist-check + audit-log path) against a real temporary
allowlist root on disk, exactly like a live agent turn would, just with
a hand-crafted malicious `path` instead of a model-produced one.

What this script can and can't prove:
  - `..` traversal, sibling-directory-prefix, and symlink escape (the
    Linux analog of a Windows directory junction) are genuinely OS-
    portable and get exercised for real here.
  - drive-relative paths, UNC paths, and 8.3 short names are Windows
    filesystem concepts with no meaningful Linux equivalent — reported
    as N/A on this OS rather than faked.
  - The "with sandbox underneath" column needs an actual container
    boundary. This script checks whether a Docker daemon is reachable
    and reports precisely why not when it isn't, rather than silently
    skipping it.

Run (from this directory, no Ollama needed): uv run python verify_policy.py
"""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.measure import append_jsonl, update_results_md  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from audit import record as audit_record  # noqa: E402
from policy import Allowlist, PolicyViolation  # noqa: E402
from tools import DISPATCH, TOOL_ACTIONS  # noqa: E402

HERE = Path(__file__).parent
ATTACKS_LOG = HERE / "measurements" / "attacks.jsonl"
RESULTS_MD = HERE / "measurements" / "results.md"
IS_WINDOWS = platform.system() == "Windows"


def gated_call(allowlist: Allowlist, audit_log: Path, tool_name: str, args: dict):
    """Same gate `agent.py`'s real gated_call() applies, factored out
    here so this script can drive it against a throwaway allowlist root
    per attack instead of the one fixed at agent.py import time (which
    is pinned to WORKSPACE_ROOT / a hardcoded sandbox/ dir).
    """
    action, path_keys = TOOL_ACTIONS[tool_name]
    audit_target = ", ".join(str(args[k]) for k in path_keys)
    resolved = {}
    try:
        for key in path_keys:
            resolved[key] = allowlist.check(args[key])
    except PolicyViolation as e:
        audit_record(audit_log, action, audit_target, allowed=False, reason=str(e))
        raise
    call_args = {**args, **{k: str(v) for k, v in resolved.items()}}
    result = DISPATCH[tool_name](**call_args)
    audit_record(audit_log, action, audit_target, allowed=True)
    return result


def attempt(allowlist: Allowlist, audit_log: Path, path: str) -> tuple[bool, str]:
    """Returns (blocked, detail). blocked=True means the allowlist did
    its job; blocked=False means the read actually succeeded, i.e. the
    attack escaped.
    """
    try:
        content = gated_call(allowlist, audit_log, "read_file", {"path": path})
        return False, f"ESCAPED — read {len(content)} bytes from outside the allowlist"
    except PolicyViolation as e:
        return True, str(e)
    except Exception as e:  # not-a-PolicyViolation failure is still not a clean "blocked"
        return False, f"unexpected error, not a policy block: {e}"


def run_dotdot_traversal(root: Path, audit_log: Path) -> dict:
    outside = root.parent / "secret.txt"
    outside.write_text("classified", encoding="utf-8")
    allowlist = Allowlist([str(root)])
    blocked, detail = attempt(allowlist, audit_log, str(root / ".." / "secret.txt"))
    return {"attack": "dotdot_traversal", "blocked": blocked, "detail": detail}


def run_sibling_prefix(root: Path, audit_log: Path) -> dict:
    evil = root.parent / (root.name + "-evil")
    evil.mkdir(exist_ok=True)
    (evil / "secret.txt").write_text("classified", encoding="utf-8")
    allowlist = Allowlist([str(root)])
    blocked, detail = attempt(allowlist, audit_log, str(evil / "secret.txt"))
    return {"attack": "sibling_prefix", "blocked": blocked, "detail": detail}


def run_symlink_escape(root: Path, audit_log: Path) -> dict:
    outside = root.parent / "secret_dir"
    outside.mkdir(exist_ok=True)
    (outside / "data.txt").write_text("classified", encoding="utf-8")
    link = root / "escape"
    if not link.exists():
        link.symlink_to(outside, target_is_directory=True)
    allowlist = Allowlist([str(root)])
    blocked, detail = attempt(allowlist, audit_log, str(link / "data.txt"))
    return {
        "attack": "symlink_escape_junction_analog",
        "blocked": blocked,
        "detail": detail,
    }


def check_docker_sandbox() -> dict:
    docker_path = shutil.which("docker")
    if not docker_path:
        return {"available": False, "reason": "docker CLI not installed in this environment"}
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
    except Exception as e:
        return {"available": False, "reason": f"docker CLI present but `docker info` failed: {e}"}
    if result.returncode != 0:
        reason = (result.stderr or result.stdout).strip().splitlines()[-1:] or ["unknown error"]
        return {
            "available": False,
            "reason": f"docker CLI installed but no daemon reachable: {reason[0]}",
        }
    return {"available": True, "reason": "docker daemon reachable"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="p3-verify-") as tmp:
        tmp_path = Path(tmp)
        root = tmp_path / "workspace"
        root.mkdir()
        audit_log = tmp_path / "audit.jsonl"

        results = [
            run_dotdot_traversal(root, audit_log),
            run_sibling_prefix(root, audit_log),
            run_symlink_escape(root, audit_log),
        ]

        # Copy this run's audit trail into the project's real measurements/
        # dir so "every attempt, including refused ones, is logged" is
        # demonstrated with real entries, not asserted in prose.
        HERE.joinpath("measurements").mkdir(exist_ok=True)
        audit_dest = HERE / "measurements" / "verify_policy_audit.jsonl"
        audit_dest.write_text(audit_log.read_text(encoding="utf-8"), encoding="utf-8")

    docker_status = check_docker_sandbox()

    for r in results:
        append_jsonl(ATTACKS_LOG, r)
        print(f"[{r['attack']}] blocked={r['blocked']} — {r['detail']}", flush=True)
    print(f"[docker sandbox] available={docker_status['available']} — {docker_status['reason']}", flush=True)

    row = lambda attack, python_col: f"| {attack} | {python_col} | {docker_col(docker_status)} |"

    def docker_col(status: dict) -> str:
        if status["available"]:
            return "pending — daemon reachable, but the container-boundary test itself isn't automated yet"
        return "pending — no Docker daemon in this environment (see Takeaway)"

    by_attack = {r["attack"]: r for r in results}

    def mark(attack_key: str) -> str:
        r = by_attack[attack_key]
        symbol = "✓ blocked" if r["blocked"] else "✗ ESCAPED"
        return f"{symbol} (`verify_policy.py`, real allowlist + audit log, no mocking)"

    windows_only_col = (
        "pending — this script hasn't implemented the real Windows-specific check yet, "
        "even though it's running on Windows"
        if IS_WINDOWS
        else "N/A on this OS — Windows-only concept, doesn't reproduce on Linux"
    )

    table_rows = [
        "| Attack | Python allowlist only | With sandbox underneath |",
        "|---|---|---|",
        row("`..` traversal", mark("dotdot_traversal")),
        row("drive-relative paths (`C:foo`)", windows_only_col),
        row("UNC paths (`\\\\?\\C:\\...`)", windows_only_col),
        row(
            "directory junctions (`mklink /J`)",
            mark("symlink_escape_junction_analog") + " — Linux symlink analog; real junction needs Windows",
        ),
        row(
            "sibling-prefix directory (bonus, not in original 6)",
            mark("sibling_prefix"),
        ),
        row(
            "case-insensitivity tricks",
            "N/A on this OS — ext4 is case-sensitive by default, nothing to bypass",
        ),
        row("8.3 short names (`PROGRA~1`)", windows_only_col),
    ]

    takeaway = (
        f"Ran for real on {platform.system()} via `verify_policy.py` (no mocking, no Ollama): "
        f"{'all 3' if all(r['blocked'] for r in results) else 'NOT all'} of the OS-portable attacks "
        f"(`..` traversal, sibling-directory-prefix, symlink escape) were blocked by "
        f"`Allowlist.check()`, and each attempt — including the refusals — landed a real entry in "
        f"measurements/verify_policy_audit.jsonl. Docker sandbox column: {docker_status['reason']}. "
        "The 3 genuinely Windows-only attacks (drive-relative, UNC, 8.3 short names) and the whole "
        "container-boundary column remain open and need a real Windows/Docker-daemon machine — see README."
    )

    update_results_md(
        RESULTS_MD,
        {
            "attack-table": "\n".join(table_rows),
            "takeaway": takeaway,
        },
    )
    print(f"\nWrote {ATTACKS_LOG} and regenerated {RESULTS_MD}", flush=True)


if __name__ == "__main__":
    main()
