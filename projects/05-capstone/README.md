# 5. Capstone — initializer/coding-agent pattern

Target: a tiny CLI to-do app (`target/todo.py`), spec'd once in `contract.py` and built up one command per fresh process.

## Build

- [x] `initializer.py` — runs once:
  - [x] writes `target/feature_list.json` (every feature initially `false`)
  - [x] writes `target/CONTRACT.md` (the CLI spec the coding agent and the tests both work from — `contract.py` is the single source of truth for both)
  - [x] copies `target/tests/` from `tests_template/` — the fixed ground-truth test suite, one file per feature, authored once and never touched by the model
  - [x] writes `target/init.ps1` — NOT `init.sh`, say so explicitly in the coding agent's own prompt too
  - [x] `git init` + first commit in `target/`
  - [x] `git config core.autocrlf true` before that first commit
- [x] `coding_agent.py` — runs fresh every invocation:
  - [x] reads `feature_list.json` and `git log` **first**, before doing anything else
  - [x] picks exactly one unfinished feature
  - [x] implements it via a Project 1-style read_file/write_file tool loop scoped to `target/` (no `run_command` — the harness alone runs tests and commits, never the model)
  - [x] verifies it with Project 4's `evaluate_deterministic()` against that feature's fixed pytest file — the model's own `TASK_COMPLETE` self-report is logged but never trusted as the commit trigger; on rejection, retries with the evaluator's feedback (bounded `MAX_RETRIES`)
  - [x] `write_file` refuses to touch `feature_list.json` or anything under `tests/`, and `tests/` is also restored from git before every evaluation — the model can't mark its own homework
  - [x] commits before the process ends
  - [x] invokes every subprocess as `uv run python ...` explicitly — don't rely on inherited `PATH`
- [x] `run_loop.ps1` — drives N fresh `python coding_agent.py` processes in a real loop (`for ($i=1; $i -le 10; $i++) { ... }`), so each iteration is genuinely a new process, not a re-used one; `-NoFeatureList`/`-NoGitLog`/`-NoCommit` switches drive the three ablation configurations below via env vars, no code edits needed

## What this is actually testing

The two failure modes the whole ladder has been building toward:
- the agent trying to one-shot the entire project instead of one feature at a time
- the agent declaring victory too early (this is where Project 4's evaluator pattern should get reused inside `coding_agent.py`, not just left behind)

## Done when

The loop runs unattended across several restarts and ends with a working, incrementally-built app and a clean git history (one commit per feature, no giant "everything" commits, no `.sh` file confusion).

## Measure

`uv run python measure.py` (from this directory; needs Ollama reachable — defaults to `qwen3.5:4b`, pass `--model <name>` or set `HARNESS_MODEL` for whatever you actually have pulled) automates all four configs: it wipes and reinitializes `target/` per config, drives `--iterations` (default 10) genuinely fresh `coding_agent.py` subprocesses the same way `run_loop.ps1` does, checks the real ground-truth tests after every iteration (not the model's own self-report) to find the first iteration where the whole app actually works, and regenerates `measurements/results.md` with iterations-to-done, git-history shape, and an auto-derived failure mode per ablation:

1. Baseline: full harness (feature list + git-log read + commit-per-session)
2. `--configs no_feature_list` — agent must infer what's done from git log + reading `todo.py` alone
3. `--configs no_gitlog` — agent only has `feature_list.json`
4. `--configs no_commit` — agent may or may not commit

Run a cheap subset first with `--configs baseline --iterations 3`; a full `uv run python measure.py` run is 4 configs × 10 sessions = 40 real model sessions. Validate the harness itself first with `uv run python measure.py --dry-run` (see Status).

Which single ablation breaks the run fastest/worst — recorded automatically in the Takeaway — is carrying the most assumption weight, and it's the first one to re-test when a better local model becomes available.

## Files

- `contract.py` — the CLI spec + ordered feature ladder, imported by both `initializer.py` and `coding_agent.py` so the spec the model gets and the spec the tests check can't drift apart
- `initializer.py`
- `init.ps1` — copied into `target/` by the initializer
- `tests_template/` — the fixed ground-truth test suite, copied into `target/tests/` by the initializer (kept here, not in `target/`, since `target/` is gitignored)
- `coding_agent.py` — also carries a `HARNESS_DRY_RUN=1`-gated scripted reference model, used only by `measure.py --dry-run`
- `test_coding_agent.py` — mocked unit tests (no live Ollama in this authoring environment; real git + pytest subprocess calls against a throwaway `target/`-like repo under `tmp_path`)
- `run_loop.ps1` — the original PowerShell driver; `measure.py` is the cross-platform, jsonl-logging, results.md-writing equivalent
- `measure.py` — automates the Measure step above
- `target/` — the actual app being built (created by initializer, git-tracked separately from this repo, gitignored here)
- `measurements/results.md`

## Status

Code (`contract.py`, `initializer.py`, `init.ps1`, `tests_template/` × 5 feature tests, `coding_agent.py`, `measure.py`) and mocked unit tests are done — `uv run pytest projects/05-capstone/` passes 15/15. `initializer.py` was run for real in this authoring environment (real `git init`/commit, no Ollama needed) and produces a clean `target/` with all 5 features pending; the 10 template tests were also verified for real against a hand-written reference `todo.py` in a scratch directory (all pass; a stub `todo.py` correctly fails them, confirming they're not vacuous). `measure.py --dry-run` was also run for real here: all 4 configs (baseline + 3 ablations) drove real subprocesses, real git commits, and real pytest evaluation end to end without crashing, using a scripted stand-in model (`HARNESS_DRY_RUN=1`) that writes the full reference `todo.py` in one shot rather than one feature per session like a real model would — so its iteration counts aren't representative of real pacing, but it did catch two real, structural findings worth keeping: with `ABLATE_NO_FEATURE_LIST`, nothing in the harness can tell it's done once the app actually works (no early stop, wasted sessions keep running), and with `ABLATE_NO_COMMIT`, `feature_list.json` keeps advancing on disk even though git history — the harness's supposed source of truth — never moves past the initializer's first commit. This environment has no Ollama, so the actual multi-process loop against a live model — and all four real `measurements/results.md` runs (baseline + 3 ablations) — are still open. Do that next: `uv run python measure.py` (add `--model <name>` if you're not using `qwen3.5:4b`).
