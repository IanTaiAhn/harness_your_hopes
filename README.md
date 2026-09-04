# harness_your_hopes

Learning agent-harness engineering by building against local models. Start here:

1. [`learning-agent-harnesses-locally.md`](./learning-agent-harnesses-locally.md) — the why and the full project ladder
2. [`harness-failure-modes.md`](./harness-failure-modes.md) — one-page map of failure mode → harness addition → measurement, per project
3. [`manual-testing-guide.md`](./manual-testing-guide.md) — layer-by-layer breakdown of each project plus hands-on steps for surfacing its specific shortcomings
4. [`PLAN.md`](./PLAN.md) — progress tracker, update as you complete each project's Build/Done-when/Measure steps
5. [`projects/`](./projects/) — one folder per rung of the ladder, each with a `README.md` (actionable checklist) and stub code to fill in
6. [`common/`](./common/) — shared Ollama client used by every project

Setup (once): see the "Local setup (Windows)" section of the main doc, then the Environment checklist in `PLAN.md`.

## Running each project

Run every command from the project's own directory (e.g. `cd projects/01-bare-metal-loop`). All of them need the setup above done first (Ollama running, `uv sync` completed).

| Project | Command |
|---|---|
| 1. Bare-metal tool loop | `uv run python agent.py "read this file, count the lines, write the count to a new file"` (omit the task string to use that same default) |
| 2. Survive a restart | `uv run python agent.py` (no arguments — runs the hardcoded default task via `seed_plan()`; kill and rerun to test resume) |
| 2.5 Context overflow | See `projects/025-context-overflow/README.md` — not yet wired into a runnable agent loop |
| 3. Permission-gated file agent | `$env:WORKSPACE_ROOT="C:\path\to\folder"` then `uv run python agent.py "organize the files in the workspace by extension"` (omit `WORKSPACE_ROOT` to default to a local `sandbox/` folder) |
| 4. Generator–evaluator loop | `uv run python run_suite.py` to drive all 20 tasks, or `uv run python -c "from generator import generate; print(generate('write tasks/solutions/x.py with def f(): return 1'))"` for a single one-off |
| 5. Capstone | `uv run python initializer.py` once, then `uv run python coding_agent.py` per session, or `.\run_loop.ps1 -Iterations 10` to drive N fresh sessions in a loop (add `-NoFeatureList`/`-NoGitLog`/`-NoCommit` for the ablation runs) |

Each project's own `README.md` and the matching section of `manual-testing-guide.md` have the fuller picture — required env vars, expected output, and what to try breaking once the happy path works.

## Automating the Measure step

Every project except 2.5 now has a `measure.py` (Project 3: `verify_policy.py`) that drives its Measure section for real instead of hand-transcribing trial results: it runs the actual trials, logs each one's outcome — including *why* it failed, not just pass/fail — to a `measurements/*.jsonl` file, and rewrites `measurements/results.md`'s tables from that log (prose outside the `<!-- MEASURE:BEGIN ... -->` markers is left alone). Run every command from the project's own directory. Every command below defaults to model `qwen3.5:4b`; pass `--model <name>` (or set `HARNESS_MODEL`) if that's not what you have pulled — check with `ollama list` first. Run with `--dry-run` first (a scripted stand-in model, no Ollama needed) to confirm the harness plumbing itself is correct before spending real inference time on it.

| Project | Command |
|---|---|
| 1. Bare-metal tool loop | `uv run python measure.py` — 40 trials (retry on/off × 4B/9B × 10), needs both models pulled (or `--models qwen3.5:4b` for just one) |
| 2. Survive a restart | `uv run python measure.py` — 5 kill-point trials + the structured-vs-naive crossover-length sweep. `--skip-kill`/`--skip-crossover` to run just one half |
| 2.5 Context overflow | Not built yet — see `projects/025-context-overflow/README.md` |
| 3. Permission-gated file agent | `uv run python verify_policy.py` — **no Ollama needed**, drives the real allowlist against a real temp directory |
| 4. Generator–evaluator loop | `uv run python run_suite.py --model qwen3.5:4b` then again with `--model qwen3.5:9b` (each is a full 20-task run); `uv run python render_results.py` to rebuild `results.md` from existing logs without re-running |
| 5. Capstone | `uv run python measure.py` — baseline + all 3 ablations, 10 sessions each by default. Scope down first with `--configs baseline --iterations 3` |

See each project's own README "Measure" section for the full flag list and what each measurement means.
