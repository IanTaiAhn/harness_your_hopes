# 2. Survive a restart

Extends Project 1. Copy `tools.py` over (or import it) — the new work is state persistence.

## Build

- [ ] `state.py`: structured progress file (JSON) — task description, steps completed, steps remaining, last tool result
- [ ] Atomic writes: write to a temp file, then `os.replace()` onto the real path
- [ ] `agent.py`: on startup, read the progress file if it exists and resume instead of restarting the task
- [ ] Handle `PermissionError` from a file the previous (killed) run had open — retry with backoff, don't crash

## Windows specifics

- [ ] Kill test: `taskkill /F /PID <pid>` (not `Ctrl+C` — that's a graceful signal your code might catch)
- [ ] Confirm `os.replace()` really is atomic in your test (it is, on Windows, same-volume)

## Done when

Hard-kill the process at 5 different points during a multi-step task. Every restart resumes exactly where it left off — no re-done work, no confusion about state. Test all 5 points, not just one.

## Measure

1. Structured progress file (this project): does it hold up across all 5 kill points?
2. Naive alternative: replay the last N raw messages into a fresh session instead of reading structured state. At what task length (turn count) does replay start losing track, on the 4B, while the structured file keeps working?
3. Record the crossover point in `measurements/results.md`.

## Files

- `state.py` — progress file read/write (atomic)
- `agent.py` — Project 1's loop + resume-from-state
- `measurements/results.md`
