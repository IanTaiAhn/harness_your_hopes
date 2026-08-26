# 3. Permission-gated file agent

Move to WSL2 or a container for this one — isolation stops being optional here.

## Build

- [x] `policy.py`: allowlist of directories the agent may touch, checked via `Path.resolve()` compared against resolved allowlist roots — never raw string comparison
- [x] Manual confirmation prompt before any destructive action (delete, overwrite) — fails closed (refuses) when stdin isn't a TTY, e.g. inside a container, rather than blocking forever on `input()`
- [x] `audit.py`: append-only log of every tool call attempted, including refused ones (timestamp, action, path, allowed/refused)
- [ ] Real OS-level boundary underneath the allowlist — pick one:
  - [ ] Docker Desktop container, only the target folder bind-mounted (`Dockerfile` is written and `WORKSPACE_ROOT`-driven; not yet built/run — no Docker daemon in the environment this was authored in, see Status)
  - [ ] Windows Sandbox (Pro/Enterprise)
  - [ ] WSL2 container or `bwrap`
- [x] Agent task: organize/rename files in a real messy folder inside the sandbox (`list_dir`/`move_file`/`delete_file` added to Project 1's tools in this project's own `tools.py`, gated the same as `read_file`/`write_file`)

## Attack list (Windows-specific)

Run each against the Python-only allowlist first, record pass/fail, then rerun with the sandbox underneath:

- [x] `..` traversal — blocked (mocked test in `test_policy.py`), portable to any OS
- [ ] drive-relative paths (`C:foo`) — Windows-only concept, needs a real Windows run
- [ ] UNC paths (`\\?\C:\...`) — Windows-only concept, needs a real Windows run
- [ ] directory junctions (`mklink /J`) — Linux analog (symlink escape) is blocked and covered in `test_policy.py`; the real junction needs a Windows run
- [ ] case-insensitivity tricks — Linux filesystems are case-sensitive by default, so this doesn't reproduce here; needs a real Windows run
- [ ] 8.3 short names (`PROGRA~1`) — Windows-only concept, needs a real Windows run

## Done when

The agent cannot touch anything outside its allowlist even under deliberate attack, and you have a complete audit trail — including every refused attempt.

## Measure

Record all 5 attack results against Python-allowlist-only, then all 5 again with the sandbox underneath, in `measurements/results.md`. The gap between those two counts is the lesson — expect Python-only to leak on at least one.

## Status

Code is implemented and covered by mocked unit tests (`uv run pytest projects/03-permission-gated-agent`) that fake `chat()`, so the policy gate, confirmation logic, and audit trail are all verified without a real model or a real sandbox. This was authored in a Linux environment with no Docker daemon and no `bwrap` available, so the container boundary itself (the actual "Done when" criterion) is written but unverified — `docker build`/`docker run` against the `Dockerfile`, and the 5 Windows-specific attacks in `measurements/results.md`, still need to run for real on a Windows/Docker machine before this project's Measure step is complete.

Two design decisions worth knowing about if you pick this up: (1) `move_file` checks **both** `src` and `dest` against the allowlist — an agent that could move a file to an unchecked destination could exfiltrate data as easily as one that could read outside the allowlist directly. (2) `run_command` from Project 1 is deliberately **not** in this project's tool set — a path-based allowlist has no single `path` argument to check in an arbitrary shell command string, so gating it here would be a false sense of security; the container boundary is what actually has to stop it, which is exactly the point this project is trying to make.

## Files

- `policy.py` — allowlist + path resolution
- `audit.py` — append-only action log
- `tools.py` — Project 1's `read_file`/`write_file` plus `list_dir`/`move_file`/`delete_file`, needed to actually organize a folder
- `agent.py` — Project 1/2's loop + policy gate + audit calls on every tool invocation
- `Dockerfile` (or Windows Sandbox `.wsb` config) — the enforcement boundary
- `test_policy.py`, `test_tools.py`, `test_agent.py` — mocked unit tests (no live Ollama or container needed)
- `measurements/results.md`
