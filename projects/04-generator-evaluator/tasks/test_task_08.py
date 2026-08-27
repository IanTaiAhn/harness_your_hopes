"""Ground-truth check for task_08_caesar_encrypt -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_caesar_encrypt(load_solution):
    m = load_solution('task_08_caesar_encrypt')
    assert m.caesar_encrypt('abc', 1) == 'bcd'
    assert m.caesar_encrypt('xyz', 3) == 'abc'
    assert m.caesar_encrypt('ABC xyz!', 2) == 'CDE zab!'
    assert m.caesar_encrypt('abc', -1) == 'zab'
    assert m.caesar_encrypt('abc', 27) == 'bcd'
