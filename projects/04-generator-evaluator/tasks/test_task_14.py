"""Ground-truth check for task_14_run_length_decode -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_run_length_decode(load_solution):
    m = load_solution('task_14_run_length_decode')
    assert m.run_length_decode('3a2b1c') == 'aaabbc'
    assert m.run_length_decode('1a1b1c') == 'abc'
    assert m.run_length_decode('12a') == 'a' * 12
    assert m.run_length_decode('') == ''
