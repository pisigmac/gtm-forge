"""Cannibalization detection."""

from gtm_forge.skills.seo.brief import Page, find_cannibals, jaccard, token_set


def test_jaccard():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert jaccard(set(), {"a"}) == 0.0


def test_token_set():
    assert token_set("Hello, World! 123") == {"hello", "world", "123"}


def test_find_cannibals_flags_overlap():
    pages = [
        Page(url="/a", title="email marketing guide", keywords=["email marketing", "guide"]),
        Page(url="/b", title="email marketing guide", keywords=["email marketing", "guide"]),
        Page(url="/c", title="sales compensation plans", keywords=["sales", "compensation"]),
    ]
    conflicts = find_cannibals(pages, threshold=0.8)
    assert len(conflicts) == 1
    assert {conflicts[0].url_a, conflicts[0].url_b} == {"/a", "/b"}


def test_distinct_pages_no_conflict():
    pages = [
        Page(url="/a", title="email marketing", keywords=["email"]),
        Page(url="/b", title="kubernetes logging", keywords=["k8s"]),
    ]
    assert find_cannibals(pages, threshold=0.6) == []
