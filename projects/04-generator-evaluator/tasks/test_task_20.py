"""Ground-truth check for task_20_title_case -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_title_case(load_solution):
    m = load_solution('task_20_title_case')
    # Small words (articles/short prepositions/conjunctions)
    # stay lowercase unless first -- one specific, defensible
    # reading of the deliberately open-ended prompt above.
    assert m.title_case('the lord of the rings') == 'The Lord of the Rings'
    assert m.title_case('a tale of two cities') == 'A Tale of Two Cities'
    assert m.title_case('war and peace') == 'War and Peace'
