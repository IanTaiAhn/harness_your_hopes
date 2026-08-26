# Project 3 — Measurement Log

| Attack | Python allowlist only | With sandbox underneath |
|---|---|---|
| `..` traversal | ✓ (mocked, `test_policy.py`) | pending — needs Docker on Windows |
| drive-relative paths (`C:foo`) | pending — Windows-only, needs real Windows | pending |
| UNC paths (`\\?\C:\...`) | pending — Windows-only, needs real Windows | pending |
| directory junctions (`mklink /J`) | ✓ Linux analog only — symlink escape blocked (mocked, `test_policy.py`); real junction pending | pending |
| case-insensitivity tricks | N/A on Linux (case-sensitive filesystem) — pending real Windows | pending |
| 8.3 short names (`PROGRA~1`) | pending — Windows-only, needs real Windows | pending |

(✓ blocked / ✗ escaped)

## Takeaway

This was authored and unit-tested in a Linux environment with no Docker daemon and no `bwrap` available, so only the two OS-portable rows above could actually be exercised here, and only against the Python-only allowlist — never against a real container boundary. What's confirmed so far: `Path.resolve()` + `is_relative_to()` correctly blocks both `..` traversal and a symlink pointing outside the allowlisted root (the sibling-directory-with-shared-prefix case is also covered, since a naive string-prefix check would wrongly allow `workspace-evil/` under an allowlist for `workspace/`).

The remaining rows, and the entire "with sandbox underneath" column, need someone to run this for real on a Windows machine with Docker Desktop: `docker build -t harness-p3 -f projects/03-permission-gated-agent/Dockerfile .` from the repo root, then `docker run --rm -v <messy-folder>:/workspace:rw harness-p3`, then attempt each attack against the running agent. Expect Python-only to leak on at least one Windows-specific technique (per the project's own prediction) and the sandboxed run to block all six.
