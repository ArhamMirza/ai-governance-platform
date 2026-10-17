"""Telling which AI tool a web address belongs to.

Pure functions. A tool is known by one or more domains, and an address
belongs to it when its host *is* that domain or a subdomain of it. The check
is on whole labels: ``chatgpt.com.evil.net`` and ``notchatgpt.com`` are not
``chatgpt.com``, which is the mistake a plain ``endswith`` or ``in`` makes.
"""

import ipaddress
import re
from collections.abc import Iterable
from typing import TypeVar
from urllib.parse import urlsplit

from app.core.exceptions import ValidationError

_LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
MAX_DOMAIN_LENGTH = 253

T = TypeVar("T")


def normalize_domain(text: str) -> str:
    """The bare lower-case host from whatever was typed -- a domain, a URL
    with a path, a host with a port. Non-ASCII names are stored as their
    punycode form so a look-alike spelling can't pass for the real one.
    Raises ValidationError for anything that isn't a plain domain name."""
    raw = text.strip().lower()
    if not raw:
        raise ValidationError("Enter a domain, such as chat.example.com.")
    has_marker = "://" in raw or raw.startswith("//")
    host = urlsplit(raw if has_marker else f"//{raw}").hostname or ""
    host = host.rstrip(".")
    if not host:
        raise ValidationError(f'"{text.strip()}" is not a domain.')
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise ValidationError(f'"{text.strip()}" is not a valid domain.') from error
    if len(host) > MAX_DOMAIN_LENGTH:
        raise ValidationError("That domain is too long.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValidationError("Use a domain name, not an IP address.")
    labels = host.split(".")
    if len(labels) < 2 or not all(_LABEL.match(label) for label in labels):
        raise ValidationError(f'"{text.strip()}" is not a valid domain.')
    return host


def host_matches(host: str, domain: str) -> bool:
    """Whether `host` is `domain` or a subdomain of it, label for label."""
    host = host.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def best_match(host: str, entries: Iterable[tuple[str, T]]) -> T | None:
    """Of the (domain, value) pairs, the value whose domain matches `host`
    most specifically -- the longest domain, so ``gemini.google.com`` can
    belong to its own tool rather than to a broader ``google.com`` one."""
    best: tuple[int, T] | None = None
    for domain, value in entries:
        if host_matches(host, domain) and (best is None or len(domain) > best[0]):
            best = (len(domain), value)
    return None if best is None else best[1]
