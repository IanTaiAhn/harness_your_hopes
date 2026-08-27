"""Ground-truth check for task_09_word_frequency -- the evaluator's only source of truth. Excluded from repo-wide pytest collection by ../tasks/conftest.py; run directly by evaluator.evaluate_deterministic().
"""
def test_word_frequency(load_solution):
    m = load_solution('task_09_word_frequency')
    result = m.word_frequency('The cat sat on the mat. The cat ran.')
    # case-insensitive, punctuation stripped -- a plausible but
    # unstated reading of the ambiguous prompt above, which is
    # exactly the kind of gap this project measures.
    assert result['the'] == 3
    assert result['cat'] == 2
    assert 'mat.' not in result
    assert result['mat'] == 1
