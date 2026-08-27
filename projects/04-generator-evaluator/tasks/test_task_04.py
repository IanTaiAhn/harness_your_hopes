"""Ground-truth check for task_04_sum_of_digits -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_sum_of_digits(load_solution):
    m = load_solution('task_04_sum_of_digits')
    assert m.sum_of_digits(123) == 6
    assert m.sum_of_digits(-123) == 6
    assert m.sum_of_digits(0) == 0
    assert m.sum_of_digits(-7) == 7
