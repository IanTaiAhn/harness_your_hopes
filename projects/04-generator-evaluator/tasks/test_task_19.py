"""Ground-truth check for task_19_rotate_list -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_rotate_list(load_solution):
    m = load_solution('task_19_rotate_list')
    # rotate RIGHT -- a plausible but unstated reading of the
    # ambiguous prompt above (it never says which direction).
    assert m.rotate_list([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert m.rotate_list([1, 2, 3], 0) == [1, 2, 3]
    assert m.rotate_list([1, 2, 3], 4) == [3, 1, 2]
    assert m.rotate_list([], 3) == []
