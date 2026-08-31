def test_remove_item_deletes_it(cli):
    cli("add", "buy milk")

    removed = cli("remove", "1")
    assert removed.returncode == 0
    assert "Removed #1" in removed.stdout

    listing = cli("list")
    assert "buy milk" not in listing.stdout


def test_remove_missing_id_reports_it(cli):
    result = cli("remove", "99")
    assert "no item with id 99" in result.stdout.lower()
