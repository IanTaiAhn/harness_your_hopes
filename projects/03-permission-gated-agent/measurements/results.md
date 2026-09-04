# Project 3 — Measurement Log

Regenerate the table below with `uv run python verify_policy.py` (from this directory — no Ollama needed, this drives `agent.gated_call()` directly against a real temp allowlist root, not a mocked one). Raw per-attack detail (resolved path, audit log entry) lives in `measurements/attacks.jsonl`.

<!-- MEASURE:BEGIN attack-table -->
| Attack | Python allowlist only | With sandbox underneath |
|---|---|---|
| `..` traversal | ✓ blocked (`verify_policy.py`, real allowlist + audit log, no mocking) | pending — no Docker daemon in this environment (see Takeaway) |
| drive-relative paths (`C:foo`) | N/A on this OS — Windows-only concept, doesn't reproduce on Linux | pending — no Docker daemon in this environment (see Takeaway) |
| UNC paths (`\\?\C:\...`) | N/A on this OS — Windows-only concept, doesn't reproduce on Linux | pending — no Docker daemon in this environment (see Takeaway) |
| directory junctions (`mklink /J`) | ✓ blocked (`verify_policy.py`, real allowlist + audit log, no mocking) — Linux symlink analog; real junction needs Windows | pending — no Docker daemon in this environment (see Takeaway) |
| sibling-prefix directory (bonus, not in original 6) | ✓ blocked (`verify_policy.py`, real allowlist + audit log, no mocking) | pending — no Docker daemon in this environment (see Takeaway) |
| case-insensitivity tricks | N/A on this OS — ext4 is case-sensitive by default, nothing to bypass | pending — no Docker daemon in this environment (see Takeaway) |
| 8.3 short names (`PROGRA~1`) | N/A on this OS — Windows-only concept, doesn't reproduce on Linux | pending — no Docker daemon in this environment (see Takeaway) |
<!-- MEASURE:END attack-table -->

(✓ blocked / ✗ escaped / N/A not applicable on this OS)

## Takeaway

<!-- MEASURE:BEGIN takeaway -->
Ran for real on Linux via `verify_policy.py` (no mocking, no Ollama): all 3 of the OS-portable attacks (`..` traversal, sibling-directory-prefix, symlink escape) were blocked by `Allowlist.check()`, and each attempt — including the refusals — landed a real entry in measurements/verify_policy_audit.jsonl. Docker sandbox column: docker CLI installed but no daemon reachable: failed to connect to the docker API at unix:///var/run/docker.sock; check if the path is correct and if the daemon is running: dial unix /var/run/docker.sock: connect: no such file or directory. The 3 genuinely Windows-only attacks (drive-relative, UNC, 8.3 short names) and the whole container-boundary column remain open and need a real Windows/Docker-daemon machine — see README.
<!-- MEASURE:END takeaway -->
