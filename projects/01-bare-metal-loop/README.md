# 1. Bare-metal tool loop

## Build

A raw agent loop in plain Python against Ollama's endpoint — no framework.

- [ ] `tools.py`: `read_file`, `write_file`, `run_command` — each with a JSON schema for tool-calling
- [ ] `agent.py`: loop = model → parse tool call → execute → feed result back → repeat until done or max-iteration guard trips
- [ ] Malformed tool-call JSON: catch it, feed the parse error back to the model as a tool result, retry (bounded)
- [ ] Max-iteration guard (e.g. 15 turns) that fails loudly, not silently

## Windows specifics

- [ ] `run_command` shells to `cmd`/PowerShell, not `sh` — state which one in the tool's description
- [ ] Expect the model to try Unix commands (`ls`, `cat`, `rm`) anyway — decide: translate, or reject with a clear error?
- [ ] `pathlib.Path` everywhere; one normalization point for `/` vs `\` in model-supplied paths
- [ ] `encoding="utf-8"` on every file open
- [ ] `subprocess.run(..., shell=False, timeout=...)` with an argument list, never a raw string

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
- `measurements/results.md` — trial log
