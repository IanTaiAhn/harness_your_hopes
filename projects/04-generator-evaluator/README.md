# 4. Generator–evaluator loop

## Build

- [x] `generator.py`: produces a code solution for a task (reuses Project 1's write_file/read_file tool loop)
- [x] `evaluator.py`: checks the solution — deterministic (`pytest` exit code) wherever the criterion is expressible as a test; a second model-as-judge call only when it genuinely isn't
- [x] Retry loop: on evaluator failure, feed the evaluator's specific feedback (failing test name + assertion, not just "failed") back to the generator and retry, bounded (`run_suite.py`, `MAX_RETRIES = 2`)

## Windows note

Prefer deterministic evaluators heavily — a second model call is a full extra context load on CPU, which is expensive on this hardware. `pytest` exit codes are free.

## Done when

The harness catches at least one real case where the generator claimed success but the evaluator correctly rejected it, and the retry-with-feedback attempt then succeeds.

## Measure

1. Run 20 tasks: `uv run python run_suite.py --model qwen3.5:4b` (needs Ollama reachable with that model pulled). For each, this logs the generator's *self-reported* success (did it claim "done"?) and the evaluator's *verified* success (did the test actually pass?) to `measurements/runs_qwen35_4b.jsonl`, and regenerates `measurements/results.md` automatically at the end.
2. The gap between self-reported and verified success rate is computed for you at the bottom of that run and in `results.md`. This gap is the headline number for the whole ladder.
3. Repeat on the 9B: `uv run python run_suite.py --model qwen3.5:9b` — does the gap narrow? `results.md`'s Takeaway is auto-filled once both jsonl logs exist. Re-render without re-running either suite with `uv run python render_results.py`.

## Files

- `generator.py`
- `evaluator.py`
- `run_suite.py` — drives all 20 tasks through generate -> evaluate -> retry-with-feedback, for one `--model` at a time; regenerates `results.md` at the end unless `--no-render`
- `render_results.py` — rebuilds `measurements/results.md` from whatever `measurements/runs_*.jsonl` already exist, without re-running anything
- `tasks/` — the 20 task specs (`taskNN_*.json`) + their pytest checks (`test_taskNN.py`); `conftest.py` excludes the checks from repo-wide `pytest` runs (they fail by design until a generator run writes a solution) while still letting `evaluator.py` run each one directly by path
- `test_generator.py`, `test_evaluator.py`, `test_run_suite.py` — mocked unit tests (no live Ollama in this authoring environment, see note below)
- `measurements/results.md`

## Status

Code (`generator.py`, `evaluator.py`, `run_suite.py`), the 20 task specs + pytest checks, and mocked unit tests are done — `uv run pytest projects/04-generator-evaluator/` passes 15/15, and a throwaway set of reference solutions (not committed) confirmed all 20 checks encode the intended behavior, including the deliberately ambiguous ones (`task_09_word_frequency`, `task_17_is_anagram`, `task_19_rotate_list`, `task_20_title_case`) where the prompt under-specifies a detail the test still pins down. This authoring environment has no Ollama, so the actual 20-task run against `qwen3.5:4b`/`qwen3.5:9b` and the `measurements/results.md` fill-in are still open — do that next.
