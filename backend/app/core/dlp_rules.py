"""What a data-loss-prevention rule may look for -- and what it may not.

The rules are *evaluated* in the browser, on the employee's machine: the text
being pasted never reaches this server. The server only stores the rules and
hands them to the browser extension, so what it must do here is refuse rules
that could misbehave when they run there -- a pattern that matches everything,
or one that makes the page freeze.

Three kinds of rule:
  builtin   a named detector the extension implements (card numbers with a
            check digit, keys and tokens, national IDs ...)
  keywords  a list of words or phrases, matched case-insensitively
  regex     a pattern, restricted to the subset that behaves the same in
            Python and in JavaScript and can't backtrack catastrophically
"""

import re

from app.core.exceptions import ValidationError

# key -> (label, what it catches). The detectors themselves live in the
# frontend (src/shared/dlp/detectors.ts), shared by the extension and the
# rule tester so what the tester says is what the browser does; a test checks
# the two lists stay in step.
BUILTIN_DETECTORS: dict[str, tuple[str, str]] = {
    "credit_card": ("Payment card number", "13 to 19 digits that pass the card check-digit test."),
    "iban": ("Bank account (IBAN)", "An international bank account number that passes its check."),
    "us_ssn": ("US Social Security number", "Nine digits written 123-45-6789."),
    "uk_nino": ("UK National Insurance number", "Two letters, six digits and a letter."),
    "pk_cnic": ("Pakistan CNIC number", "Thirteen digits written 12345-1234567-1."),
    "api_key": (
        "API key or access token",
        "Well-known key formats (cloud, source-control, payment and chat providers).",
    ),
    "private_key": ("Private key", "A block beginning -----BEGIN ... PRIVATE KEY-----."),
    "jwt": ("Signed web token (JWT)", "Three base64 sections separated by dots, starting eyJ."),
    "password_assignment": (
        "Password in plain text",
        "password = ..., pwd: ... and similar assignments with a value.",
    ),
}

MAX_PATTERN_LENGTH = 300
MAX_KEYWORDS = 200
MIN_KEYWORD_LENGTH = 3
MAX_KEYWORD_LENGTH = 100

# Group openers that mean the same in Python and JavaScript and can't be used
# to do anything exotic: a plain non-capturing group and the two lookaheads.
_SAFE_GROUP_OPENERS = (":", "=", "!")
# A group that is itself repeated and contains a repeat -- (a+)+, (.*a)*,
# (x|y*)+ -- is the classic way to make a regex take exponential time.
_NESTED_REPEAT = re.compile(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*(?:[+*]|\{\d*,?\d*\})")
_BACKREFERENCE = re.compile(r"\\(?:[1-9]|k<)")


def validate_builtin(key: str | None) -> str:
    if key is None or key not in BUILTIN_DETECTORS:
        raise ValidationError("Choose one of the built-in detectors.")
    return key


def validate_keywords(keywords: list[str] | None) -> list[str]:
    """Trimmed, de-duplicated ignoring case, in the order given."""
    seen: dict[str, str] = {}
    for keyword in keywords or []:
        text = keyword.strip()
        if not text:
            continue
        if not MIN_KEYWORD_LENGTH <= len(text) <= MAX_KEYWORD_LENGTH:
            raise ValidationError(
                f'"{text[:30]}" must be {MIN_KEYWORD_LENGTH} to {MAX_KEYWORD_LENGTH} characters '
                "-- a shorter word would match inside everyday text."
            )
        seen.setdefault(text.lower(), text)
    if not seen:
        raise ValidationError("Add at least one word or phrase to look for.")
    if len(seen) > MAX_KEYWORDS:
        raise ValidationError(f"A rule can look for at most {MAX_KEYWORDS} words or phrases.")
    return list(seen.values())


def validate_pattern(pattern: str | None) -> str:
    """The pattern if it is safe to run in a browser, else ValidationError
    saying why."""
    text = (pattern or "").strip()
    if not text:
        raise ValidationError("Enter the pattern to look for.")
    if len(text) > MAX_PATTERN_LENGTH:
        raise ValidationError(f"A pattern can be at most {MAX_PATTERN_LENGTH} characters.")
    try:
        compiled = re.compile(text)
    except re.error as error:
        raise ValidationError(f"That isn't a valid pattern: {error}.") from error
    for index in _group_openers(text):
        if text[index + 2 : index + 3] not in _SAFE_GROUP_OPENERS:
            raise ValidationError(
                "Only plain groups (?:...) and lookaheads (?=...) (?!...) are allowed: named "
                "groups, lookbehinds, flags and comments behave differently in the browser."
            )
    if _BACKREFERENCE.search(text):
        raise ValidationError("Back-references aren't allowed.")
    if _NESTED_REPEAT.search(text):
        raise ValidationError(
            "A repeated group that itself repeats, such as (a+)+, can freeze the page. "
            "Simplify the pattern."
        )
    if compiled.search(""):
        raise ValidationError("That pattern matches empty text, so it would match everything.")
    return text


def _group_openers(text: str) -> list[int]:
    """Positions of each "(?" that isn't escaped or inside a character class."""
    positions = []
    in_class = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            in_class = True
        elif char == "]":
            in_class = False
        elif char == "(" and not in_class and text[index + 1 : index + 2] == "?":
            positions.append(index)
        index += 1
    return positions
