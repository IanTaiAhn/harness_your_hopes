# 3. Permission-gated file agent

Move to WSL2 or a container for this one — isolation stops being optional here.

## Build

- [ ] `policy.py`: allowlist of directories the agent may touch, checked via `Path.resolve()` compared against resolved allowlist roots — never raw string comparison
- [ ] Manual confirmation prompt before any destructive action (delete, overwrite)
- [ ] `audit.py`: append-only log of every tool call attempted, including refused ones (timestamp, action, path, allowed/refused)
- [ ] Real OS-level boundary underneath the allowlist — pick one:
  - [ ] Docker Desktop container, only the target folder bind-mounted
  - [ ] Windows Sandbox (Pro/Enterprise)
  - [ ] WSL2 container or `bwrap`
- [ ] Agent task: organize/rename files in a real messy folder inside the sandbox

## Attack list (Windows-specific)

Run each against the Python-only allowlist first, record pass/fail, then rerun with the sandbox underneath:

- [ ] `..` traversal
- [ ] drive-relative paths (`C:foo`)
- [ ] UNC paths (`\\?\C:\...`)
- [ ] directory junctions (`mklink /J`)
- [ ] case-insensitivity tricks
- [ ] 8.3 short names (`PROGRA~1`)

## Done when

The agent cannot touch anything outside its allowlist even under deliberate attack, and you have a complete audit trail — including every refused attempt.

## Measure

Record all 5 attack results against Python-allowlist-only, then all 5 again with the sandbox underneath, in `measurements/results.md`. The gap between those two counts is the lesson — expect Python-only to leak on at least one.

## Files

- `policy.py` — allowlist + path resolution
- `audit.py` — append-only action log
- `agent.py` — Project 1/2's loop + policy gate + audit calls on every tool invocation
- `Dockerfile` (or Windows Sandbox `.wsb` config) — the enforcement boundary
- `measurements/results.md`
