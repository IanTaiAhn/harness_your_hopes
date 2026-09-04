# Project 5 — Measurement Log

Regenerate with `uv run python measure.py --model <your-model>` (from this directory; defaults to `qwen3.5:4b`, or set `HARNESS_MODEL` — needs Ollama reachable with that model. Each config runs `--iterations` fresh `coding_agent.py` subprocesses, default 10, so a full real run is 4 configs × 10 sessions = 40 real model sessions). Validate the harness itself first with `uv run python measure.py --dry-run` (scripted reference `todo.py`, no Ollama). Raw per-iteration detail (test-pass counts, commit counts, stdout tail) lives in `measurements/runs.jsonl`.

## Baseline (full harness)

<!-- MEASURE:BEGIN baseline -->
(not run yet)
<!-- MEASURE:END baseline -->

## Ablation: remove feature list

<!-- MEASURE:BEGIN no_feature_list -->
(not run yet)
<!-- MEASURE:END no_feature_list -->

## Ablation: remove git-log read

<!-- MEASURE:BEGIN no_gitlog -->
(not run yet)
<!-- MEASURE:END no_gitlog -->

## Ablation: remove commit-per-session requirement

<!-- MEASURE:BEGIN no_commit -->
(not run yet)
<!-- MEASURE:END no_commit -->

## Takeaway

<!-- MEASURE:BEGIN takeaway -->
<!-- Which single ablation broke the run fastest/worst? That's the component carrying the most assumption weight. -->
<!-- MEASURE:END takeaway -->
