"""Ground-truth check for task_15_gcd_lcm -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_gcd_lcm(load_solution):
    m = load_solution('task_15_gcd_lcm')
    assert m.gcd_lcm(12, 18) == (6, 36)
    assert m.gcd_lcm(7, 13) == (1, 91)
    assert m.gcd_lcm(5, 5) == (5, 5)
