"""Ground-truth check for task_16_transpose -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_transpose(load_solution):
    m = load_solution('task_16_transpose')
    assert m.transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]
    assert m.transpose([[1]]) == [[1]]
