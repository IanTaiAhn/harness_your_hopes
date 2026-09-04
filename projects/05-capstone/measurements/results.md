# Project 5 — Measurement Log

Regenerate with `uv run python measure.py` (from this directory; needs Ollama + `qwen3.5:4b` reachable — each config runs `--iterations` fresh `coding_agent.py` subprocesses, default 10, so a full real run is 4 configs × 10 sessions = 40 real model sessions). Validated dry (`--dry-run`, scripted reference `todo.py`, no Ollama) — all 4 configs ran end to end without crashing, including the `no_feature_list`/`no_commit` edge cases, confirming the harness plumbing itself is correct. No real (Ollama-backed) trials recorded yet, and the dry run's numbers aren't representative of real pacing (the scripted stand-in front-loads the whole solution into session 1, where a real model would build one feature per session) — see README's Status section.

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
