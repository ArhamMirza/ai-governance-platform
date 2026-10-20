"""What counts as an email address here.

One rule for every place an address is typed or sent: creating an account,
the first registration, a CSV import and the browser extension's reports. It
catches typos (`bob@x`, `bob@@company.com`, `bob company.com`), not fakes:
nothing short of sending a message proves a mailbox is real or belongs to the
person, and looking the domain up would fail offline and tell a third party
who is on the platform.

Written as plain checks rather than one pattern, so there is no way to make it
slow with a long odd string.
"""

MAX_LENGTH = 320
MAX_LOCAL = 64
MAX_LABEL = 63

MESSAGE = "That doesn't look like an email address. Check it for a typo."


def normalise(raw: str) -> str:
    """The form an address is stored and compared in."""
    return raw.strip().lower()


def problem_with(email: str) -> str | None:
    """Why an address is not acceptable, or None. Expects it already normalised."""
    if not email or len(email) > MAX_LENGTH or any(ch.isspace() for ch in email):
        return MESSAGE
    local, at, domain = email.partition("@")
    if not at or "@" in domain or not local or len(local) > MAX_LOCAL:
        return MESSAGE
    labels = domain.split(".")
    if len(labels) < 2:
        return MESSAGE
    for label in labels:
        if not label or len(label) > MAX_LABEL or label.startswith("-") or label.endswith("-"):
            return MESSAGE
    last = labels[-1]
    if len(last) < 2 or last.isdigit():
        return MESSAGE
    return None


def is_valid(email: str) -> bool:
    return problem_with(email) is None
