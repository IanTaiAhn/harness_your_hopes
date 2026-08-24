# Learning Harness Engineering with Local Models

A project-based path for learning how agent harnesses work, built entirely offline on a normal Windows laptop (16 GB system RAM, integrated or modest GPU). No cloud API keys, no external calls — everything runs on localhost.

---

## Why this matters

A harness is everything wrapped around a model that turns raw text prediction into reliable work getting done: tool definitions, permission logic, state/memory management, verification loops, and session handoff.

Anthropic's framing is the best mental model: **every component in a harness encodes an assumption about what the model can't do on its own** — and those assumptions go stale as models improve, so they have to be re-tested rather than set once. That idea is load-bearing for this whole plan, and it's why every project below ends with a measurement step instead of just a build step.

Small local models are a good teacher here. They fail in exactly the ways frontier models fail less often — malformed tool calls, premature "done" claims, lost context — so the harness's job becomes obvious fast instead of staying theoretical.

---

## Local setup (Windows)

### Runtime

**Ollama for Windows.** Download the installer from `ollama.com/download` and run it — there's no shell one-liner on Windows. It installs as a background service and exposes an OpenAI-compatible endpoint at `http://localhost:11434/v1`. Nothing leaves your machine.

Verify it's up before writing any code:

```powershell
curl.exe http://localhost:11434/api/tags
```

(Use `curl.exe`, not `curl` — bare `curl` in PowerShell is an alias for `Invoke-WebRequest` with different flags.)

### Models

| Role | Model | Size | When to use |
|---|---|---|---|
| Default / daily driver | `qwen3.5:4b` | ~3.4 GB | Writing and debugging harness code. Use this 90% of the time. |
| Real test runs | `qwen3.5:9b` | ~6.6 GB | Verifying a project's "done when" criteria. |

```powershell
ollama pull qwen3.5:4b
ollama pull qwen3.5:9b
```

Qwen remains the most stable local family for tool calling — the lowest rate of dropped calls and invalid JSON, which is the load-bearing skill for everything below. Confirm tool support before trusting it:

```powershell
ollama show qwen3.5:4b
```

Look for `tools` under Capabilities. Do this per model — capabilities differ within a family.

### Hardware reality check (read this before you're confused later)

16 GB of *system* RAM on a laptop without a real GPU means:

- **The 9B is slow.** Expect single-digit tokens/sec on CPU. An agent loop resends a growing context every turn, so prompt processing — not generation — will dominate your wall-clock time. A four-step task can take minutes. Budget for it.
- **The 4B is the default, not the fallback.** Invert the usual advice. Develop on the 4B; promote to the 9B only for scored runs.
- **Don't keep both loaded.** Set these as user environment variables (System Properties → Environment Variables), then restart the Ollama service:
  - `OLLAMA_MAX_LOADED_MODELS=1`
  - `OLLAMA_KEEP_ALIVE=5m`
  - `OLLAMA_MODELS=D:\ollama\models` (optional — models are several GB each and default to your C: user profile)
- **Set `num_ctx` explicitly on every request.** Ollama's default context window is small and it will silently truncate your history. This looks exactly like "the model forgot what it was doing," and you will lose a day to it. Start at 8192, log actual token counts each turn, and treat the ceiling as a real constraint — it becomes Project 2.5.
- **Close Chrome.** Not a joke. A 9B Q4 model plus your IDE plus a browser on 16 GB will push you into pagefile swapping, and swap-thrashing looks like a hung agent.

### Environment

Use `uv` from the start, since Project 4 shells out to `pytest`. Install it once via the installer at `astral.sh/uv` (or `winget install astral-sh.uv`), then in the repo root:

```powershell
uv sync
```

This reads `pyproject.toml`, creates `.venv`, and installs `requests` + `pytest` — no separate activate step needed since every script below is invoked as `uv run ...`. If you'd rather activate it directly: `.\.venv\Scripts\Activate.ps1`.

If script execution is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**Decide now: native Windows or WSL2.** Native is simpler to start and forces you to confront real Windows path/process behavior, which is honest harness work. WSL2 gives you Linux tooling and much better sandboxing options for Project 3. Recommendation: **start native for Projects 1–2, move to WSL2 or a container at Project 3**, when isolation stops being optional. Ollama runs on Windows and is reachable from WSL2 over `localhost`, so you don't need to reinstall it.

---

## The project ladder

Each project builds on the last and maps to a specific harness concept. Each one ends with a **measure** step — that's the part that turns this from learning patterns into learning engineering.

### 1. Bare-metal tool loop

**Build:** A raw agent loop in plain Python against Ollama's endpoint — no framework. Give it 2–3 local tools: `read_file`, `write_file`, `run_command`. The loop is: model → tool call → your code executes it → result fed back → repeat until done or a max-iteration guard trips.

**Windows specifics:**
- Your `run_command` tool is running through `cmd` or PowerShell, not `sh`. Decide which, write it into the tool description, and expect the model to try Unix commands anyway — `ls`, `cat`, `rm`. Handling that mismatch *is* harness work.
- Use `pathlib.Path` throughout. Never string-concatenate paths; the model will hand you a mix of `/` and `\` and you need one normalization point.
- Set `encoding="utf-8"` on every file open. Windows defaults to the system codepage and will mangle anything the model writes with non-ASCII characters.
- Always pass `shell=False` with an argument list to `subprocess.run`, and always set a `timeout`.

**What it teaches:** The loop itself is trivial. The error handling around it — retrying malformed tool-call JSON, catching a model that ignores its own tool schema, normalizing paths — is the actual harness work.

**Done when:** The agent completes a 3–4 step task (e.g. "read this file, count the lines, write the count to a new file") **8 out of 10 runs on the 4B**, with no manual intervention.

**Measure:** Delete your retry-on-malformed-JSON logic and rerun the same 10 trials. Record the delta. Then rerun both variants on the 9B. You will likely find the retry logic matters far more on the 4B — that's an assumption you just made concrete instead of assuming.

---

### 2. Survive a restart

**Build:** Extend Project 1 so task state is written to disk as a structured progress file, not just held in memory. Kill the Python process mid-task, restart it, and have it resume correctly by reading that file.

**Windows specifics:**
- Kill it properly: `Ctrl+C` is a graceful signal your code might catch and cleanly finish. Use `taskkill /F /PID <pid>` for a genuinely abrupt death — that's the case you're designing for.
- Write the progress file atomically: write to a temp file, then `os.replace()`. A half-written JSON file after a hard kill is the exact failure this project exists to prevent, and `os.replace` is atomic on Windows.
- Windows holds file locks aggressively. If the agent has a file open when it dies, the next run may hit `PermissionError`. Handle it explicitly rather than crashing.

**What it teaches:** A small-scale rebuild of Anthropic's "engineers on shifts" problem — each new session starts with zero memory, and the harness is what bridges the gap.

**Done when:** You can hard-kill the process at any point and the next run picks up exactly where it left off — no re-work, no confusion about what's already done. Test this at five different points in the task, not one.

**Measure:** Compare the structured progress file against the naive alternative — just replaying the last N messages into the next session. On the 4B, at what task length does replay start failing and the structured file keep working? That crossover point is why the structured file exists.

---

### 2.5. Run out of context on purpose

**Build:** Take the Project 2 agent and give it a task that provably exceeds your `num_ctx`. Read a large file in chunks, or run 30+ tool calls. Then implement a strategy for what survives: summarize old turns, drop tool outputs but keep tool *calls*, or do a full reset and rebuild the session from the progress file alone.

**What it teaches:** Context management is arguably *the* central harness concern, and it's the one that motivated the full-context-reset design in Anthropic's harness posts — summarization-as-compaction wasn't sufficient for very long jobs. On 16 GB you'll hit this ceiling much sooner than a frontier setup would, which makes it easier to study, not harder.

**Done when:** The agent completes a task requiring more than `num_ctx` tokens of history without losing track of what it already did.

**Measure:** Implement two of the three strategies above and score them on the same task. Then halve `num_ctx` and rerun. A strategy that only works with headroom isn't a strategy.

---

### 3. Permission-gated file agent

**Build:** Point the agent at a real, messy local folder and have it organize and rename files. Add an explicit allowlist of directories it may touch, require manual confirmation before any destructive action (delete, overwrite), and log every tool call to an audit file.

**The important correction:** an allowlist checked inside your own Python is still the agent's own code policing itself — one path-handling bug away from useless. The actual argument in Anthropic's *Beyond permission prompts* is that prompt- and application-level gating isn't sufficient; you want OS-level isolation underneath it. So build the allowlist **and** put a real boundary under it:

- **Easiest on Windows:** run the agent inside a Docker Desktop container with only the target folder bind-mounted. Everything else is simply not present.
- **Alternative:** Windows Sandbox (Pro/Enterprise, enable via Windows Features) for a disposable VM.
- **In WSL2:** a container, or `bwrap` if you want the Linux-native version of this.

Then attack your own allowlist deliberately. On Windows the interesting attacks are: `..` traversal, drive-relative paths (`C:foo`), UNC paths (`\\?\C:\...`), directory junctions (`mklink /J`), case-insensitivity tricks, and 8.3 short names (`PROGRA~1`). Resolve with `Path.resolve()` and compare against the resolved allowlist root — never compare raw strings.

**What it teaches:** Permissions and approvals as a designed system with a real enforcement boundary, rather than a prompt-level suggestion.

**Done when:** The agent cannot touch anything outside its allowlist even when you actively try to make it, and you have a full audit trail of every action attempted — including the refused ones.

**Measure:** Try five escape techniques from the list above against the Python allowlist alone. Record which ones work. Then rerun with the container underneath. The gap between those two numbers is the entire lesson.

---

### 4. Generator–evaluator loop

*(Moved ahead of the capstone — the capstone's main failure mode is premature "done" claims, and this is the tool that catches them.)*

**Build:** Split "produce an answer" and "check the answer" into two separate roles instead of trusting the model's self-report. A generator writes code or a solution; an evaluator checks it — a deterministic test wherever possible, a second model call as judge only where a test genuinely can't express the criterion. On failure, the harness retries with the evaluator's feedback attached.

**Windows note:** prefer deterministic evaluators heavily here. A second model call costs you another full context load on CPU, which on this hardware is expensive. `pytest` exit codes are free.

**What it teaches:** Self-reported "done" is the failure mode you're designing against. This pattern is the deciding factor in most reliable agent systems — Claude Code's `/goal` ships essentially this loop, with a separate fast model checking a completion condition each turn.

**Done when:** The harness catches at least one real case where the generator claimed success and the evaluator correctly rejected it — and the retry-with-feedback then succeeds.

**Measure:** Log generator self-reported success rate against evaluator-verified success rate across 20 tasks. The gap between those two numbers is the single most useful thing you'll learn in this whole plan. Then check whether the gap narrows on the 9B — that's the assumption-expiry effect happening in miniature.

---

### 5. Capstone — the initializer/coding-agent pattern

**Build:** Recreate Anthropic's two-agent long-running harness on a tiny local coding target (a CLI to-do app, or a small Flask app):

- **Initializer agent:** runs once. Writes a `feature_list.json` (every feature initially `false`), an init script, and an initial git commit.
- **Coding agent:** on every fresh run, reads the progress file and `git log` *first*, picks one unfinished feature, implements it, tests it, and commits before ending the session.

Run it as a literal loop across multiple fresh Python processes to simulate real context-window resets.

**Windows specifics:**
- The init script is `init.ps1` or `init.bat`, not `init.sh`. Say so in the initializer's prompt, or you'll get bash and the model will never notice it failed.
- Set `git config core.autocrlf true` before the first commit. Otherwise line-ending churn will make every diff look enormous and your `git log` handoff signal becomes noise.
- Verify with `pytest` via subprocess, or `curl.exe` against a dev server on a fixed port. **Skip browser automation** — it's more than you need and it won't fit in your RAM budget alongside a 9B model.
- Invoke every subprocess as `uv run python ...` explicitly. Don't rely on `PATH` inheriting correctly across a fresh process.
- Drive the outer loop from a PowerShell script (`for ($i=1; $i -le 10; $i++) { uv run python agent.py }`) so each iteration really is a fresh process.

**What it teaches:** Everything from 1–4 combined, plus the two failure modes that motivated the whole design: the agent trying to one-shot the entire project, and the agent declaring victory too early.

**Done when:** You can run the loop unattended across several restarts and end up with a working, incrementally-built app and a clean git history.

**Measure:** Ablate one component at a time — remove the feature list, then the git-log read, then the commit-per-session requirement — and rerun. Which single component, removed, breaks the run fastest? That component is carrying the most assumption weight, and it's the one to re-test first when you eventually swap in a better model.

---

## Stretch goal (later, not next)

Multi-agent orchestration — a planner spinning up parallel subagents — is the natural next step, but small quantized models degrade quickly at multi-step planning, and on 16 GB you cannot hold two models in memory simultaneously anyway. Attempt this only once 1–5 are solid, and ideally on better hardware. Otherwise you'll spend your time fighting the model instead of learning harness design.

---

## Reference reading

- Anthropic — *Effective harnesses for long-running agents* (Nov 2025) — the two-agent initializer/coding pattern that Project 5 recreates.
- Anthropic — *Harness design for long-running application development* (Mar 2026) — the source of the "every component encodes an expiring assumption" framing.
- Anthropic — *Beyond permission prompts* — the sandboxing-over-prompting argument behind Project 3.
- Anthropic — *Building effective agents* (Dec 2024) — the foundation the harness posts build on.
- `github.com/anthropics/cwc-long-running-agents` — the same patterns as short, readable, standalone primitives. The most directly useful thing on this list while you're actually building.