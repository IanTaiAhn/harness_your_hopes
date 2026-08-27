"""Ground-truth check for task_05_is_prime -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_is_prime(load_solution):
    m = load_solution('task_05_is_prime')
    assert m.is_prime(2) is True
    assert m.is_prime(17) is True
    assert m.is_prime(1) is False
    assert m.is_prime(0) is False
    assert m.is_prime(-5) is False
    assert m.is_prime(9) is False
