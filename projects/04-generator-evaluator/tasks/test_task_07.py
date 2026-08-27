"""Ground-truth check for task_07_dedupe -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_dedupe(load_solution):
    m = load_solution('task_07_dedupe')
    assert m.dedupe([1, 2, 1, 3, 2, 4]) == [1, 2, 3, 4]
    assert m.dedupe([]) == []
    assert m.dedupe(['a', 'b', 'a']) == ['a', 'b']
