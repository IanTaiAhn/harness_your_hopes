# 5. Capstone — initializer/coding-agent pattern

Target: a tiny local coding project (CLI to-do app, or a small Flask app) — pick one and put it in `target/`.

## Build

- [ ] `initializer.py` — runs once:
  - [ ] writes `target/feature_list.json` (every feature initially `false`)
  - [ ] writes `target/init.ps1` (or `.bat`) — NOT `init.sh`, say so explicitly in the initializer's own prompt
  - [ ] `git init` + first commit in `target/`
  - [ ] `git config core.autocrlf true` before that first commit
- [ ] `coding_agent.py` — runs fresh every invocation:
  - [ ] reads `feature_list.json` and `git log` **first**, before doing anything else
  - [ ] picks exactly one unfinished feature
  - [ ] implements it, tests it (pytest via subprocess, or `curl.exe` against a fixed dev port — **skip browser automation**, out of RAM budget)
  - [ ] commits before the process ends
  - [ ] invokes every subprocess as `uv run python ...` explicitly — don't rely on inherited `PATH`
- [ ] `run_loop.ps1` — drives N fresh `python coding_agent.py` processes in a real loop (`for ($i=1; $i -le 10; $i++) { ... }`), so each iteration is genuinely a new process, not a re-used one

## What this is actually testing

The two failure modes the whole ladder has been building toward:
- the agent trying to one-shot the entire project instead of one feature at a time
- the agent declaring victory too early (this is where Project 4's evaluator pattern should get reused inside `coding_agent.py`, not just left behind)

## Done when

The loop runs unattended across several restarts and ends with a working, incrementally-built app and a clean git history (one commit per feature, no giant "everything" commits, no `.sh` file confusion).

## Measure

Ablate one component at a time and rerun the full loop from scratch each time:

1. Baseline: full harness (feature list + git-log read + commit-per-session), record how many iterations to a working app
2. Remove the feature list (agent must infer what's done from git log alone)
3. Remove the git-log read (agent only has feature_list.json)
4. Remove the commit-per-session requirement (agent may or may not commit)

Record which single ablation breaks the run fastest/worst in `measurements/results.md` — that component is carrying the most assumption weight, and it's the first one to re-test when a better local model becomes available.

## Files

- `initializer.py`
- `coding_agent.py`
- `run_loop.ps1`
- `target/` — the actual app being built (created by initializer, git-tracked separately from this repo)
- `measurements/results.md`
