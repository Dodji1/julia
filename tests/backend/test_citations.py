from backend.rag.citations import strip_citations, verify_citations


def test_renumbers_in_order_of_first_appearance(make_passage):
    p1, p2, p3 = make_passage(1), make_passage(2), make_passage(3)
    result = verify_citations("Règle A [P3]. Règle B [P1]. Rappel [P3].", {"P1": p1, "P2": p2, "P3": p3})

    assert result.answer_markdown == "Règle A [1]. Règle B [2]. Rappel [1]."
    assert result.sources == (p3, p1)
    assert result.discarded == ()


def test_grouped_labels_are_split_and_deduplicated(make_passage):
    p1, p2 = make_passage(1), make_passage(2)
    result = verify_citations("Règle [P2, P1]. Encore [P1; P1].", {"P1": p1, "P2": p2})

    assert result.answer_markdown == "Règle [1][2]. Encore [2]."
    assert result.sources == (p2, p1)


def test_unknown_labels_are_discarded(make_passage):
    p1 = make_passage(1)
    result = verify_citations("Règle inventée [P9]. Règle sourcée [P1].", {"P1": p1})

    assert result.answer_markdown == "Règle inventée. Règle sourcée [1]."
    assert result.sources == (p1,)
    assert result.discarded == ("P9",)


def test_bare_numbers_written_by_the_model_are_removed(make_passage):
    p1 = make_passage(1)
    result = verify_citations("Règle [1]. Autre règle [P1].", {"P1": p1})

    assert result.answer_markdown == "Règle. Autre règle [1]."
    assert result.discarded == ("[1]",)


def test_lowercase_labels_are_accepted(make_passage):
    result = verify_citations("Règle [p1].", {"P1": make_passage(1)})

    assert result.answer_markdown == "Règle [1]."


def test_answer_without_citation_has_no_source(make_passage):
    result = verify_citations("Une affirmation sans fondement.", {"P1": make_passage(1)})

    assert result.sources == ()


def test_markdown_links_and_indentation_are_preserved(make_passage):
    text = "Voir [le guide](https://dgi.bj) [P1] :\n  - point imbriqué [P1]"
    result = verify_citations(text, {"P1": make_passage(1)})

    assert result.answer_markdown == "Voir [le guide](https://dgi.bj) [1] :\n  - point imbriqué [1]"


def test_strip_citations_removes_every_reference():
    assert strip_citations("Précisez le régime [P1] [2].") == "Précisez le régime."
