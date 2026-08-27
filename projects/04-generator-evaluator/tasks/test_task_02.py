"""Ground-truth check for task_02_is_palindrome -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_is_palindrome(load_solution):
    m = load_solution('task_02_is_palindrome')
    assert m.is_palindrome('A man, a plan, a canal: Panama') is True
    assert m.is_palindrome('racecar') is True
    assert m.is_palindrome('hello') is False
    assert m.is_palindrome('') is True
