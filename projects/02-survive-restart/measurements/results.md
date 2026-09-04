# Project 2 — Measurement Log

Regenerate with `uv run python measure.py` (from this directory). Kill-point trials need no Ollama (a fresh KILL_AFTER_TURN=0 run just needs one real turn); the crossover-length trials need Ollama + `qwen3.5:4b`. Validate the harness itself with `uv run python measure.py --dry-run` (scripted chat, no Ollama at all). Raw per-trial detail lives in `measurements/kill_trials.jsonl` and `measurements/crossover_trials.jsonl`. Validated dry: all 5 kill points resumed cleanly, and the crossover mechanism itself is real — the scripted stand-in model has no memory beyond what's literally still present in the messages it's given, so naive replay's failure is a genuine consequence of truncation, not a scripted outcome (see README Status). No real (Ollama-backed) trials recorded yet.

## Kill-point resume test

<!-- MEASURE:BEGIN kill-table -->
| Kill point (turn #) | Resumed cleanly? | Notes |
|---|---|---|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |
<!-- MEASURE:END kill-table -->

## Structured file vs. naive replay — crossover length

<!-- MEASURE:BEGIN crossover-table -->
| Task length (turns) | Structured file: correct? | Replay-last-N: correct? |
|---|---|---|
| 5 | | |
| 10 | | |
| 15 | | |
| 20 | | |
| 25 | | |
<!-- MEASURE:END crossover-table -->

<!-- MEASURE:BEGIN crossover-point -->
Crossover point (replay starts failing): `______`
<!-- MEASURE:END crossover-point -->

## Takeaway

<!-- MEASURE:BEGIN takeaway -->
<!-- Fill in: how much context/turns can naive replay tolerate before it loses track, on the 4B? -->
<!-- MEASURE:END takeaway -->
