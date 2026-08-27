"""Ground-truth check for task_12_is_valid_parentheses -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_is_valid_parentheses(load_solution):
    m = load_solution('task_12_is_valid_parentheses')
    assert m.is_valid_parentheses('()[]{}') is True
    assert m.is_valid_parentheses('([{}])') is True
    assert m.is_valid_parentheses('(]') is False
    assert m.is_valid_parentheses('([)]') is False
    assert m.is_valid_parentheses('') is True
