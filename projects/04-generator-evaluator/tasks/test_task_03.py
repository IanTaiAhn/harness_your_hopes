"""Ground-truth check for task_03_reverse_words -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_reverse_words(load_solution):
    m = load_solution('task_03_reverse_words')
    assert m.reverse_words('  the sky   is blue ') == 'blue is sky the'
    assert m.reverse_words('hello') == 'hello'
    assert m.reverse_words('a b') == 'b a'
