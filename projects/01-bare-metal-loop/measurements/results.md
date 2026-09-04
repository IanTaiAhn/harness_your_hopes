# Project 1 — Measurement Log

Regenerate this file with `uv run python measure.py` (from this directory; needs Ollama + `qwen3.5:4b`/`9b` reachable). The tables below are auto-written between the `MEASURE` marker comments — edit outside them freely, edits inside get overwritten on the next run. Raw per-trial data (including *why* a trial failed, not just pass/fail) lives in `measurements/runs.jsonl`. Validated dry (`--dry-run`, no Ollama) to confirm the harness itself is correct; no real trials recorded yet.

<!-- MEASURE:BEGIN task -->
Task used for all trials: `______________________`
<!-- MEASURE:END task -->

## Retry-on-malformed-JSON: on vs. off

<!-- MEASURE:BEGIN retry-table -->
| Model | Retry logic | Trial 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | Pass rate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4b | on  | | | | | | | | | | | |
| 4b | off | | | | | | | | | | | |
| 9b | on  | | | | | | | | | | | |
| 9b | off | | | | | | | | | | | |
<!-- MEASURE:END retry-table -->

(✓ / ✗ per trial cell)

## Takeaway

<!-- MEASURE:BEGIN takeaway -->
<!-- Fill in after all 40 trials: did retry logic matter more on the 4B than the 9B, as predicted? By how much? -->
<!-- MEASURE:END takeaway -->
