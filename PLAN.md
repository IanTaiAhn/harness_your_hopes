# Implementation Plan & Progress Tracker

Companion to [`learning-agent-harnesses-locally.md`](./learning-agent-harnesses-locally.md). That doc is the *why*; this doc is the *where am I* — update it as you move through the ladder so a stopped session (yours or a fresh Claude one) can pick up without re-reading everything.

## How to use this

- Work top to bottom. Don't start Project N+1 until Project N's "Done when" is met *and* its "Measure" step has a recorded result — the measurement is the point, not a nice-to-have.
- Each project lives in `projects/0X-slug/` with its own `README.md` (goals copied from the main doc, made actionable) and stub code to fill in.
- Log every measurement in that project's `measurements/results.md`, even failed/partial runs. The gap between two numbers is the deliverable, not the code.
- Code runs against your local Ollama on Windows/WSL2, not in a cloud sandbox — nothing here is meant to execute where it was scaffolded.

## Status legend

`[ ]` not started · `[~]` in progress · `[x]` done-when met · `[M]` measured (fully complete)

## Ladder

- [ ] `[~]` `[M]` **1. Bare-metal tool loop** — `projects/01-bare-metal-loop/`
  Raw Python loop, no framework. 3 tools: read_file, write_file, run_command.
  Done when: 8/10 runs succeed unattended on the 4B for a 3–4 step task.
  Measure: retry-on-malformed-JSON on vs. off, 4B and 9B.

- [ ] `[~]` `[M]` **2. Survive a restart** — `projects/02-survive-restart/`
  Progress file on disk, atomic writes, resume after a hard kill.
  Done when: hard-kill at 5 different points, next run resumes clean each time.
  Measure: structured progress file vs. naive replay-last-N-messages — find the crossover length where replay fails.

- [ ] `[~]` `[M]` **2.5 Run out of context on purpose** — `projects/025-context-overflow/`
  Force a task past `num_ctx`. Implement 2 of: summarize old turns, drop tool outputs, full reset from progress file.
  Done when: task needing more than `num_ctx` tokens completes without losing track.
  Measure: score both strategies on the same task, then halve `num_ctx` and rerun.

- [ ] `[~]` `[M]` **3. Permission-gated file agent** — `projects/03-permission-gated-agent/`
  Allowlist + real OS-level sandbox underneath it (Docker/Windows Sandbox/bwrap). Audit log of every action, including refused ones.
  Done when: agent can't escape the allowlist even under deliberate attack.
  Measure: try 5 escape techniques (`..` traversal, drive-relative paths, UNC paths, junctions, 8.3 short names) against Python-only allowlist, then again with the sandbox underneath. Record the gap.

- [ ] `[~]` `[M]` **4. Generator–evaluator loop** — `projects/04-generator-evaluator/`
  Separate generate vs. verify roles. Deterministic evaluator (pytest) preferred over a second model call.
  Done when: evaluator catches at least one real false "done" claim, and retry-with-feedback then succeeds.
  Measure: generator self-reported success rate vs. evaluator-verified rate, 20 tasks. Recheck the gap on the 9B.

- [ ] `[~]` `[M]` **5. Capstone — initializer/coding-agent** — `projects/05-capstone/`
  Initializer writes `feature_list.json` + init script + first commit. Coding agent reads progress + `git log` first, does one feature, tests, commits — run as N fresh processes.
  Done when: unattended run across several restarts ends with a working incrementally-built app and clean git history.
  Measure: ablate one component at a time (feature list / git-log read / commit-per-session) and see which breaks the run fastest.

## Stretch (not until 1–5 are `[M]`)

- [ ] Multi-agent orchestration — only after the ladder is solid and ideally on better hardware.

## Environment checklist (do once)

- [ ] Ollama installed, `curl.exe http://localhost:11434/api/tags` responds
- [ ] `ollama pull qwen3.5:4b` and `ollama pull qwen3.5:9b`
- [ ] `ollama show qwen3.5:4b` confirms `tools` under Capabilities (repeat for 9b)
- [ ] `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_KEEP_ALIVE=5m` set, service restarted
- [ ] `uv` installed, `uv sync` run successfully (creates `.venv`, installs deps from `pyproject.toml`)
- [ ] Decided native Windows vs. WSL2 for Projects 1–2 (move to WSL2/container at Project 3 regardless)

## Running log

Freeform notes as you go — surprises, dead ends, things that took longer than expected. Newest entry on top.

<!-- 2026-XX-XX: example entry -->
