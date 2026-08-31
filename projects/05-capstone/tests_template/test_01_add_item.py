def test_add_item_appears_in_list(cli):
    added = cli("add", "buy milk")
    assert added.returncode == 0
    assert "Added #1: buy milk" in added.stdout

    listing = cli("list")
    assert "buy milk" in listing.stdout


def test_second_item_gets_next_id(cli):
    cli("add", "buy milk")
    second = cli("add", "walk dog")
    assert "Added #2: walk dog" in second.stdout
