# 2.5 Run out of context on purpose

Extends Project 2. No new tools — the work is entirely in how you manage `messages` before it's sent to `chat()`.

## Build

Pick 2 of these 3 strategies and implement both as swappable functions applied to `messages` before each `chat()` call:

- [ ] **Summarize old turns** — collapse turns older than the last K into a single system/user message summarizing what happened (likely a second model call, or a cheap heuristic summary)
- [ ] **Drop tool outputs, keep tool calls** — strip the (often large) results of old tool calls but keep the call itself, so the model still sees *what it did*, just not the full output
- [ ] **Full reset from progress file** — discard `messages` entirely past a threshold and rebuild a fresh session from `state.py`'s progress file (Project 2) plus a short "resume" preamble

Force the overflow deliberately: read a large file in chunks, or drive 30+ tool calls in one task.

## Done when

A task requiring more than `num_ctx` tokens of history completes without the agent losing track of what it already did (repeating a step, forgetting a constraint, contradicting an earlier decision).

## Measure

1. Score both implemented strategies on the same overflow-forcing task (4B, `num_ctx=8192`).
2. Halve `num_ctx` to 4096 and rerun both. A strategy that only works with headroom isn't a strategy — record which one degrades and which one holds.

## Files

- `context_strategies.py` — the 2 chosen strategies as functions over `messages`
- `agent.py` — Project 2's loop + a strategy hook before every `chat()` call
- `measurements/results.md`
