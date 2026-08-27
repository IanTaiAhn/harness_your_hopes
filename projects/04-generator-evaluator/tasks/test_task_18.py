"""Ground-truth check for task_18_chunk_list -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_chunk_list(load_solution):
    m = load_solution('task_18_chunk_list')
    assert m.chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert m.chunk_list([1, 2, 3], 3) == [[1, 2, 3]]
    assert m.chunk_list([], 2) == []
