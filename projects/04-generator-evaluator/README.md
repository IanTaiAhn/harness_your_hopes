# 4. Generator–evaluator loop

## Build

- [ ] `generator.py`: produces a code solution for a task (reuses Project 1/2's loop)
- [ ] `evaluator.py`: checks the solution — deterministic (`pytest` exit code) wherever the criterion is expressible as a test; a second model-as-judge call only when it genuinely isn't
- [ ] Retry loop: on evaluator failure, feed the evaluator's specific feedback (failing test name + assertion, not just "failed") back to the generator and retry, bounded

## Windows note

Prefer deterministic evaluators heavily — a second model call is a full extra context load on CPU, which is expensive on this hardware. `pytest` exit codes are free.

## Done when

The harness catches at least one real case where the generator claimed success but the evaluator correctly rejected it, and the retry-with-feedback attempt then succeeds.

## Measure

1. Run 20 tasks. For each, log the generator's *self-reported* success (did it claim "done"?) and the evaluator's *verified* success (did the test actually pass?).
2. Compute the gap between self-reported and verified success rate. This gap is the headline number for the whole ladder.
3. Repeat on the 9B — does the gap narrow?

## Files

- `generator.py`
- `evaluator.py`
- `tasks/` — the 20 task specs + their pytest checks
- `measurements/results.md`
