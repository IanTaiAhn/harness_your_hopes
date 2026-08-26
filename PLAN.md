# Implementation Plan & Progress Tracker

Companion to [`learning-agent-harnesses-locally.md`](./learning-agent-harnesses-locally.md). That doc is the *why*; this doc is the *where am I* — update it as you move through the ladder so a stopped session (yours or a fresh Claude one) can pick up without re-reading everything.

## How to use this

- Work top to bottom. Don't start Project N+1 until Project N's "Done when" is met *and* its "Measure" step has a recorded result — the measurement is the point, not a nice-to-have.
- Each project lives in `projects/0X-slug/` with its own `README.md` (goals copied from the main doc, made actionable) and stub code to fill in.
- Log every measurement in that project's `measurements/results.md`, even failed/partial runs. The gap between two numbers is the deliverable, not the code.
- Code runs against your local Ollama on Windows/WSL2, not in a cloud sandbox — nothing here is meant to execute where it was scaffolded.

## Status legend

Each item below is prefixed with one of: `[ ]` not started · `[~]` in progress · `[x]` done-when met · `[M]` measured (fully complete). Update the prefix in place as a project moves forward — don't stack markers.

## Ladder

- [~] **1. Bare-metal tool loop** — `projects/01-bare-metal-loop/`
  Raw Python loop, no framework. 3 tools: read_file, write_file, run_command.
  Done when: 8/10 runs succeed unattended on the 4B for a 3–4 step task.
  Measure: retry-on-malformed-JSON on vs. off, 4B and 9B.
  Status: code + mocked unit tests done (PR TBD). Not yet run against real Ollama — do that next, then start the trial log.

- [~] **2. Survive a restart** — `projects/02-survive-restart/`
  Progress file on disk, atomic writes, resume after a hard kill.
  Done when: hard-kill at 5 different points, next run resumes clean each time.
  Measure: structured progress file vs. naive replay-last-N-messages — find the crossover length where replay fails.
  Status: code done (`state.py`, `agent.py`), merged. Not yet hard-killed for real at the 5 required points — do that next, then start the crossover-length measurement.

- [ ] **2.5 Run out of context on purpose** — `projects/025-context-overflow/`
  Force a task past `num_ctx`. Implement 2 of: summarize old turns, drop tool outputs, full reset from progress file.
  Done when: task needing more than `num_ctx` tokens completes without losing track.
  Measure: score both strategies on the same task, then halve `num_ctx` and rerun.

- [~] **3. Permission-gated file agent** — `projects/03-permission-gated-agent/`
  Allowlist + real OS-level sandbox underneath it (Docker/Windows Sandbox/bwrap). Audit log of every action, including refused ones.
  Done when: agent can't escape the allowlist even under deliberate attack.
  Measure: try 5 escape techniques (`..` traversal, drive-relative paths, UNC paths, junctions, 8.3 short names) against Python-only allowlist, then again with the sandbox underneath. Record the gap.
  Status: `policy.py`/`audit.py`/`agent.py`/`tools.py` implemented, covered by mocked unit tests. Authored in a Linux environment with no Docker daemon and no `bwrap`, so only `..` traversal and a symlink-escape analog were actually exercised (see `measurements/results.md`) — building the `Dockerfile`, running the 4 remaining Windows-specific attacks, and the sandboxed-run column are all still open and need a real Windows/Docker machine.

- [ ] **4. Generator–evaluator loop** — `projects/04-generator-evaluator/`
  Separate generate vs. verify roles. Deterministic evaluator (pytest) preferred over a second model call.
  Done when: evaluator catches at least one real false "done" claim, and retry-with-feedback then succeeds.
  Measure: generator self-reported success rate vs. evaluator-verified rate, 20 tasks. Recheck the gap on the 9B.

- [ ] **5. Capstone — initializer/coding-agent** — `projects/05-capstone/`
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

- 2026-08-26: Implemented Project 3 (`policy.py`, `audit.py`, `agent.py`, and a new `tools.py` adding `list_dir`/`move_file`/`delete_file` on top of Project 1's `read_file`/`write_file`). Two things worth remembering: (1) `move_file` checks both `src` and `dest` against the allowlist — a one-sided check would let an agent exfiltrate a file by moving it to an unchecked destination just as easily as by reading it directly. (2) `run_command` is deliberately excluded from this project's tool set: a path-based allowlist has no single `path` argument to check in an arbitrary shell command string, so "gating" it would be theater — the container boundary is what actually has to stop it. Also found and fixed a latent bug while adding this project's tests: every project reuses the same test/module basenames (`tools.py`, `agent.py`, `test_agent.py`, ...) with no `__init__.py` (the `0X-slug` directory names aren't valid package identifiers), so running the suite across more than one project at once caused pytest collection errors and, worse, silent `sys.modules` cross-contamination between projects' same-named modules. Fixed with `--import-mode=importlib` in `pyproject.toml` plus explicit `sys.modules` eviction in each test file before importing its own `agent`/`tools` — future projects reusing these basenames should follow the same pattern. This authoring environment has no Docker daemon and no `bwrap`, so the real sandbox boundary and the Windows-specific attacks are unverified — see `projects/03-permission-gated-agent/measurements/results.md`.
- 2026-08-24: Implemented Project 1 for real (`common/ollama_client.py`, `projects/01-bare-metal-loop/{agent,tools}.py`) and added mocked unit tests, since this authoring environment has no Ollama to run against. Two design notes worth remembering: (1) `chat()` targets Ollama's native `/api/chat`, not the `/v1` OpenAI-compat shim — the native endpoint is what actually accepts `options.num_ctx` and returns token counts. (2) Ollama pre-parses `tool_calls[].function.arguments` into a dict, so "malformed tool-call JSON" can't happen through that field — the real small-model failure is falling out of structured tool-calling and dumping a JSON guess into plain `content`, which is what the retry/ablation logic actually handles. First real-Ollama run and the 40-trial measurement log are still open.

<!-- 2026-XX-XX: example entry -->
