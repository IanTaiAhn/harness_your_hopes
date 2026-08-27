"""Ground-truth check for task_10_binary_search -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_binary_search(load_solution):
    m = load_solution('task_10_binary_search')
    arr = [1, 3, 5, 7, 9, 11]
    assert m.binary_search(arr, 7) == 3
    assert m.binary_search(arr, 1) == 0
    assert m.binary_search(arr, 11) == 5
    assert m.binary_search(arr, 4) == -1
    assert m.binary_search([], 1) == -1
