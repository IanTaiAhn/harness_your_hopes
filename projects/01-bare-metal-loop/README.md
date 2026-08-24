# 1. Bare-metal tool loop

## Build

A raw agent loop in plain Python against Ollama's endpoint — no framework.

- [x] `tools.py`: `read_file`, `write_file`, `run_command` — each with a JSON schema for tool-calling
- [x] `agent.py`: loop = model → parse tool call → execute → feed result back → repeat until done or max-iteration guard trips
- [x] Malformed tool-call JSON: catch it, feed the parse error back to the model as a tool result, retry (bounded)
- [x] Max-iteration guard (e.g. 15 turns) that fails loudly, not silently

Note on the malformed-JSON path: Ollama's native `/api/chat` already returns `tool_calls` with `arguments` pre-parsed into a dict, so the classic "model emitted broken JSON inside a tool call" failure mostly can't happen through that field. The realistic small-model failure is different: it drops out of structured tool-calling entirely and dumps a JSON-shaped guess into plain `content` instead. `agent.py` handles that case — the system prompt asks for a single `{"name": ..., "arguments": {...}}` object as a fallback, `_try_parse_manual_tool_call` attempts to parse it, and a parse failure is what `MAX_JSON_RETRIES` actually governs. This is the ablation switch for the Measure step below.

## Windows specifics

- [x] `run_command` shells to PowerShell, not `sh` — stated in the tool's description
- [ ] Expect the model to try Unix commands (`ls`, `cat`, `rm`) anyway — decide: translate, or reject with a clear error? (currently: reject — PowerShell just errors and that error is fed back as the tool result)
- [x] `pathlib.Path` everywhere; one normalization point (`Path(...).resolve()`) for `/` vs `\` in model-supplied paths
- [x] `encoding="utf-8"` on every file open
- [x] `subprocess.run(..., shell=False, timeout=...)` with an argument list, never a raw string

## Status

Code is implemented and covered by mocked unit tests (`uv run pytest projects/01-bare-metal-loop`) that fake `chat()` so the loop, retry, and dispatch logic run without a real model. `agent.py` prints per-turn progress (`[turn N] ...`) as it goes, since a genuinely working run on CPU can take minutes and silent output is indistinguishable from a hang.

First real run against Ollama (qwen3.5:4b, ~2000-line input file) completed successfully but undercounted lines by 1 (2058 vs. 2059). Likely cause: the tool set has no dedicated line-counter, so the model has to eyeball-count the raw file contents in its own context rather than getting an exact count from a tool — a plausible small-model failure mode worth tracking across trials, not necessarily a harness bug. Note in the trial log whether the model reached for `run_command` (e.g. `(Get-Content file).Count`) or just reasoned over the text — that distinguishes "model can't count" from "PowerShell counted differently than Notepad" (trailing-newline handling differs between the two).

## Done when

8/10 unattended runs on `qwen3.5:4b` complete a 3–4 step task (e.g. "read this file, count the lines, write the count to a new file") with no manual intervention.

## Measure

1. Run 10 trials on the 4B with retry-on-malformed-JSON enabled. Record pass/fail.
2. Disable the retry logic. Run 10 more trials on the 4B. Record pass/fail.
3. Repeat both on the 9B.
4. Record all four numbers in `measurements/results.md`. Expect the retry logic to matter far more on the 4B — confirm or refute it.

## Files

- `agent.py` — the loop
- `tools.py` — tool implementations + schemas
- `test_agent.py`, `test_tools.py` — mocked unit tests (no live Ollama needed)
- `measurements/results.md` — trial log
