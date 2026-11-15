from scripts.evaluate_due_diligence import check_expected_order, normalize_answer


def test_ranked_identifiers_must_be_in_order() -> None:
    expected = ["ORDER000001", "ORDER000002", "ORDER000003"]
    assert check_expected_order("1. ORDER000001 2. ORDER000002 3. ORDER000003", expected)
    assert not check_expected_order("1. ORDER000002 2. ORDER000001 3. ORDER000003", expected)
    assert not check_expected_order("1. ORDER000001 2. ORDER000002", expected)


def test_repeated_mentions_do_not_change_order() -> None:
    expected = ["ORDER000001", "ORDER000002"]
    assert check_expected_order("ORDER000001, ORDER000002. ORDER000001 remains first.", expected)


def test_escaped_resource_line_breaks_are_boundaries() -> None:
    answer = "ORDER000001,80\\r\\nORDER000002,70\\r\\n"
    assert check_expected_order(answer, ["ORDER000001", "ORDER000002"])
    assert "\nORDER000002" in normalize_answer(answer)
