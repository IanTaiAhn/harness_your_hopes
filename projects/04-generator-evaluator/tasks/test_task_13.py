"""Ground-truth check for task_13_run_length_encode -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_run_length_encode(load_solution):
    m = load_solution('task_13_run_length_encode')
    assert m.run_length_encode('aaabbc') == '3a2b1c'
    assert m.run_length_encode('abc') == '1a1b1c'
    assert m.run_length_encode('') == ''
