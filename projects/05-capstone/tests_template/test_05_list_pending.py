def test_list_pending_excludes_done_items(cli):
    cli("add", "buy milk")
    cli("add", "walk dog")
    cli("done", "1")

    pending = cli("list", "--pending")
    assert "walk dog" in pending.stdout
    assert "buy milk" not in pending.stdout


def test_list_pending_on_all_done_reports_no_items(cli):
    cli("add", "buy milk")
    cli("done", "1")

    pending = cli("list", "--pending")
    assert "no items" in pending.stdout.lower()
