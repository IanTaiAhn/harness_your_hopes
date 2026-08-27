"""Ground-truth check for task_06_flatten -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_flatten(load_solution):
    m = load_solution('task_06_flatten')
    assert m.flatten([1, [2, 3], [4, [5, 6]]]) == [1, 2, 3, 4, 5, 6]
    assert m.flatten([]) == []
    assert m.flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]
