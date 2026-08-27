"""Ground-truth check for task_01_fizzbuzz -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_fizzbuzz(load_solution):
    m = load_solution('task_01_fizzbuzz')
    assert m.fizzbuzz(3) == 'Fizz'
    assert m.fizzbuzz(5) == 'Buzz'
    assert m.fizzbuzz(15) == 'FizzBuzz'
    assert m.fizzbuzz(7) == '7'
