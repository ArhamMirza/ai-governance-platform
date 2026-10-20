import time

import pytest

from app.core import email_address


@pytest.mark.parametrize(
    "address",
    [
        "ada@example.com",
        "a@b.co",
        "first.last+tag@sub.example.co.uk",
        "o'brien@example.ie",
        "user_name@my-company.org",
        "elena@xn--bcher-kva.example",
        "josé@exemple.fr",
        "x" * 64 + "@example.com",
    ],
)
def test_ordinary_addresses_are_accepted(address: str) -> None:
    assert email_address.is_valid(address)


@pytest.mark.parametrize(
    "address",
    [
        "",
        "bob",
        "bob@",
        "@example.com",
        "bob@x",
        "bob@localhost",
        "bob@@example.com",
        "bob@exa@mple.com",
        "bob company@example.com",
        "bob@exam ple.com",
        "bob@example..com",
        "bob@.example.com",
        "bob@example.com.",
        "bob@-example.com",
        "bob@example-.com",
        "bob@example.c",
        "bob@example.123",
        "bob@192.168.1.1",
        "x" * 65 + "@example.com",
        "bob@" + "a" * 64 + ".com",
        "a@" + "b" * 320 + ".com",
    ],
)
def test_typos_and_malformed_addresses_are_refused_with_a_plain_message(address: str) -> None:
    assert email_address.problem_with(address) == email_address.MESSAGE


def test_normalising_trims_and_lowercases() -> None:
    assert email_address.normalise("  Ada@Example.COM \n") == "ada@example.com"


def test_a_long_odd_string_is_refused_quickly() -> None:
    nasty = "!@" + "!." * 100_000
    started = time.perf_counter()

    assert not email_address.is_valid(nasty)
    assert time.perf_counter() - started < 0.5
