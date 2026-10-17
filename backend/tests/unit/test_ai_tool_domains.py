"""Telling which AI tool a web address belongs to -- app.core.ai_tool_domains."""

import pytest

from app.core.ai_tool_domains import best_match, host_matches, normalize_domain
from app.core.exceptions import ValidationError


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("chatgpt.com", "chatgpt.com"),
        ("  ChatGPT.COM  ", "chatgpt.com"),
        ("https://chatgpt.com/c/123?model=x", "chatgpt.com"),
        ("http://chat.openai.com:8443/path", "chat.openai.com"),
        ("claude.ai/", "claude.ai"),
        ("chatgpt.com.", "chatgpt.com"),
        ("//perplexity.ai/search", "perplexity.ai"),
        # A non-ASCII look-alike is stored as punycode, so it can't pass for the real one.
        ("сlaude.ai", "xn--laude-0ye.ai"),
    ],
)
def test_whatever_was_typed_becomes_a_bare_lower_case_host(typed: str, expected: str) -> None:
    assert normalize_domain(typed) == expected


@pytest.mark.parametrize(
    "typed",
    [
        "",
        "   ",
        "localhost",
        "192.168.0.1",
        "[::1]",
        "not a domain",
        "-bad.example.com",
        "a..b.com",
    ],
)
def test_anything_that_isnt_a_domain_name_is_refused(typed: str) -> None:
    with pytest.raises(ValidationError):
        normalize_domain(typed)


def test_a_domain_that_is_too_long_is_refused() -> None:
    with pytest.raises(ValidationError):
        normalize_domain(".".join(["a" * 60] * 5) + ".com")


@pytest.mark.parametrize(
    ("host", "domain", "expected"),
    [
        ("chatgpt.com", "chatgpt.com", True),
        ("www.chatgpt.com", "chatgpt.com", True),
        ("a.b.chatgpt.com", "chatgpt.com", True),
        ("CHATGPT.COM", "chatgpt.com", True),
        ("chatgpt.com.", "chatgpt.com", True),
        # Whole labels only: these are different sites.
        ("notchatgpt.com", "chatgpt.com", False),
        ("chatgpt.com.evil.net", "chatgpt.com", False),
        ("evilchatgpt.com", "chatgpt.com", False),
        ("chatgpt.co", "chatgpt.com", False),
        ("com", "chatgpt.com", False),
        ("openai.com", "chat.openai.com", False),
    ],
)
def test_a_host_belongs_to_a_domain_only_label_for_label(
    host: str, domain: str, expected: bool
) -> None:
    assert host_matches(host, domain) is expected


def test_the_most_specific_domain_wins() -> None:
    entries = [("google.com", "Google"), ("gemini.google.com", "Gemini")]

    assert best_match("gemini.google.com", entries) == "Gemini"
    assert best_match("app.gemini.google.com", entries) == "Gemini"
    assert best_match("mail.google.com", entries) == "Google"
    # Order doesn't matter.
    assert best_match("gemini.google.com", list(reversed(entries))) == "Gemini"


def test_a_host_the_catalogue_doesnt_know_belongs_to_nothing() -> None:
    assert best_match("example.org", [("chatgpt.com", 1)]) is None
    assert best_match("example.org", []) is None
