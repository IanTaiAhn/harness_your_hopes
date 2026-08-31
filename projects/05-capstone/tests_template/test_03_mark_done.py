def test_mark_done_flips_status(cli):
    cli("add", "buy milk")

    done = cli("done", "1")
    assert done.returncode == 0
    assert "Done #1" in done.stdout

    listing = cli("list")
    line = next(line for line in listing.stdout.splitlines() if "buy milk" in line)
    assert "[x]" in line


def test_mark_done_missing_id_reports_it(cli):
    result = cli("done", "99")
    assert "no item with id 99" in result.stdout.lower()
