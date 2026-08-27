"""Ground-truth check for task_11_merge_intervals -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_merge_intervals(load_solution):
    m = load_solution('task_11_merge_intervals')
    assert m.merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
    assert m.merge_intervals([[1, 3], [3, 5]]) == [[1, 5]]
    assert m.merge_intervals([]) == []
