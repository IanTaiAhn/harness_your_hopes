"""Ground-truth check for task_17_is_anagram -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_is_anagram(load_solution):
    m = load_solution('task_17_is_anagram')
    # case-insensitive and spaces ignored -- a plausible but
    # unstated reading of the ambiguous prompt above.
    assert m.is_anagram('Listen', 'Silent') is True
    assert m.is_anagram('dormitory', 'dirty room') is True
    assert m.is_anagram('hello', 'world') is False
