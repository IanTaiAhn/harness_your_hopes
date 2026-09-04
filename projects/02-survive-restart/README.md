# 2. Survive a restart

Extends Project 1. Copy `tools.py` over (or import it) — the new work is state persistence.

## Build

- [x] `state.py`: structured progress file (JSON) — task description, steps completed, steps remaining, last tool result
- [x] Atomic writes: write to a temp file, then `os.replace()` onto the real path
- [x] `agent.py`: on startup, read the progress file if it exists and resume instead of restarting the task
- [x] Handle `PermissionError` from a file the previous (killed) run had open — retry with backoff, don't crash (`state.py`'s `_replace_with_retry`)

## Windows specifics

- [ ] Kill test: `taskkill /F /PID <pid>` (not `Ctrl+C` — that's a graceful signal your code might catch) — `measure.py` uses an in-process `KILL_AFTER_TURN`/`KILL_BEFORE_FIRST_SAVE` hook instead (see Measure below) since a real external kill can't be timed to a precise turn boundary without a race; still worth doing once on a real Windows `taskkill` too, at least once, to confirm the in-process hook and a genuine external kill behave the same
- [ ] Confirm `os.replace()` really is atomic in your test (it is, on Windows, same-volume)

## Done when

Hard-kill the process at 5 different points during a multi-step task. Every restart resumes exactly where it left off — no re-done work, no confusion about state. Test all 5 points, not just one.

## Measure

`uv run python measure.py` (from this directory) automates both halves:

1. Structured progress file (this project): does it hold up across all 5 kill points? `agent.py` supports `KILL_AFTER_TURN=<n>`/`KILL_BEFORE_FIRST_SAVE=1` env vars that hard-exit (`os._exit`, same as an external kill — skips cleanup and exception handlers) at a precise, deterministic point instead of a racy external one; `measure.py` runs all 5, then reruns each fresh and checks the resume was clean (every step done exactly once, in order, all expected files present).
2. Naive alternative: replay the last N raw messages into a fresh session instead of reading structured state (`HARNESS_REPLAY_MODE=naive`, `HARNESS_REPLAY_KEEP_LAST`). At what task length (turn count) does replay start losing track, on the 4B, while the structured file keeps working? `measure.py` drives both modes against `seed_plan_of_length(n)` synthetic tasks (content markers instead of a human judgment call) at n = 5/10/15/20/25 and checks correctness by plain string match.
3. The crossover point is filled into `measurements/results.md` automatically.

Validate the harness itself first with `uv run python measure.py --dry-run` — see Status.

## Files

- `state.py` — progress file read/write (atomic)
- `agent.py` — Project 1's loop + resume-from-state, plus the kill hooks, replay-mode switch, and synthetic-task generator `measure.py` needs
- `test_agent.py` — mocked/pure-logic unit tests (seed_plan_of_length, check_synthetic_summary, build_messages_naive, and that the kill hooks fire at the right point)
- `measure.py` — automates both halves of the Measure step above
- `measurements/results.md`

## Status

Code (`state.py`, `agent.py`) and unit tests are done — `uv run pytest projects/02-survive-restart/` passes. `measure.py --dry-run` was run for real here: all 5 kill points resumed cleanly, and the crossover comparison is genuine, not scripted to a predetermined outcome — the dry-run's stand-in model has no memory of its own; it recovers each file's content only by scanning the actual `messages` it's given, so naive mode's failure is a real consequence of the last-N-messages window truncating away early turns, while structured mode never loses the information because `build_messages()` re-includes every completed step's full text on every turn. This environment has no Ollama, so the real kill-point run (mechanically the same, just against a live model) and the real crossover-length measurement against a live model are still open — do that next: `uv run python measure.py` (defaults to `qwen3.5:4b`; pass `--model <name>` or set `HARNESS_MODEL` to point at whatever you actually have pulled).
