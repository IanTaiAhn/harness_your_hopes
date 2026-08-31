def test_list_shows_pending_marker_for_new_items(cli):
    cli("add", "buy milk")
    cli("add", "walk dog")

    listing = cli("list")
    lines = [line for line in listing.stdout.splitlines() if line.strip()]
    assert len(lines) == 2
    assert all("[ ]" in line for line in lines)
    assert any("buy milk" in line for line in lines)
    assert any("walk dog" in line for line in lines)


def test_list_on_empty_store(cli):
    listing = cli("list")
    assert "no items" in listing.stdout.lower()
