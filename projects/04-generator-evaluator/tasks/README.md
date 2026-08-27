# Task specs

20 `.json` files, one per task, shape:

```json
{
  "id": "task_01_fizzbuzz",
  "prompt": "Write a Python file at tasks/solutions/task_01_fizzbuzz.py that defines a function `fizzbuzz(n: int) -> str` ...",
  "test_file": "test_task_01.py"
}
```

Each `prompt` spells out the exact path the generator must write to
(`tasks/solutions/<id>.py`, relative to `04-generator-evaluator/` — run
`run_suite.py`/`generator.py` from that directory) and the exact function
signature expected, since `generate()` gets nothing but this string.

Paired with each spec is a `test_task_NN.py` in this same directory — the
evaluator's ground truth for that task. Each one takes the `load_solution`
fixture from `conftest.py`, which imports `solutions/<id>.py` by path and
raises a clear `AssertionError` if the generator never wrote it, rather
than a confusing import error.

`conftest.py` also sets `collect_ignore_glob = ["test_task_*.py"]`, so a
repo-wide `uv run pytest` never collects these — they're fixtures for the
evaluator, not tests of our own code, and are expected to fail until a
generator run produces a solution. `evaluator.evaluate_deterministic()`
still runs each one directly by path (`pytest tasks/test_task_NN.py -v`),
where `collect_ignore_glob` does not apply.

Most tasks are precisely specified. A few (`task_09_word_frequency`,
`task_17_is_anagram`, `task_19_rotate_list`, `task_20_title_case`)
deliberately leave a detail unstated in the prompt — the test still picks
one defensible reading and enforces it — so the self-report/verified gap
has somewhere real to show up: a model can plausibly claim success on a
different (also defensible) reading and be marked wrong by the evaluator.
