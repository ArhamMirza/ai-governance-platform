"""What counts as an acceptable password.

Length matters most, so that is the main rule. The rest only turns away what
attackers try first: the common words people build passwords from, keyboard
and number runs, a password with almost no variety, and one that is made out
of the person's own name or email. No rule about "one capital, one symbol":
those make passwords harder to remember without making them harder to guess.
"""

from app.core.exceptions import ValidationError

MIN_LENGTH = 12
MAX_LENGTH = 200

# The words most "creative" passwords are built from. Matched after the
# password has been lower-cased, common look-alike characters swapped back
# ("p@ssw0rd" -> "password") and trailing digits and symbols dropped, so
# "Password123!" is caught as well as "password".
_COMMON_WORDS = frozenset(
    {
        "password", "passw0rd", "passcode", "passphrase", "welcome", "letmein", "changeme",
        "administrator", "admin", "qwerty", "qwertyuiop", "iloveyou", "monkey", "dragon",
        "football", "baseball", "basketball", "master", "login", "secret", "sunshine",
        "princess", "superman", "batman", "trustno", "shadow", "summer", "winter", "spring",
        "autumn", "company", "computer", "internet", "starwars", "whatever", "freedom",
        "abc", "test", "testing", "default", "guest", "user", "root", "temp", "temporary",
        "governance", "compliance",
    }
)  # fmt: skip

_LOOKALIKES = str.maketrans(
    {"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"}
)

# A password that is just a stretch of one of these, forwards or backwards.
_RUNS = (
    "abcdefghijklmnopqrstuvwxyz",
    "qwertyuiopasdfghjklzxcvbnm",
    "azertyuiopqsdfghjklmwxcvbn",
    "01234567890123456789",
)

_MIN_DISTINCT_CHARACTERS = 5
_MIN_PART_LENGTH = 4


def _strip_trailing(text: str) -> str:
    end = len(text)
    while end and not text[end - 1].isalpha():
        end -= 1
    return text[:end]


def _base_word(password: str) -> str:
    # Trailing digits and symbols go first, so "Password123!" is not turned
    # into "passwordlze" by the look-alike swap before they are dropped.
    return _strip_trailing(_strip_trailing(password.lower()).translate(_LOOKALIKES))


def _is_common(password: str) -> bool:
    base = _base_word(password)
    if base in _COMMON_WORDS:
        return True
    # "letmein-letmein": nothing but a common word, over and over.
    letters = "".join(c for c in base if c.isalpha())
    return any(
        letters == word * (len(letters) // len(word))
        for word in _COMMON_WORDS
        if len(letters) % len(word) == 0
    )


def _is_a_run(lowered: str) -> bool:
    return any(lowered in run or lowered[::-1] in run for run in _RUNS)


def _personal_parts(email: str | None, name: str | None) -> list[str]:
    parts: list[str] = []
    if email:
        parts.append(email.split("@")[0])
    if name:
        parts.extend(name.split())
    return [p.lower() for p in parts if len(p) >= _MIN_PART_LENGTH]


def problem_with(password: str, *, email: str | None = None, name: str | None = None) -> str | None:
    """What is wrong with this password, in words the person can act on, or
    None when it is acceptable."""
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters. A few unrelated words works well."
    if len(password) > MAX_LENGTH:
        return f"Use at most {MAX_LENGTH} characters."

    lowered = password.lower()
    if len(set(lowered)) < _MIN_DISTINCT_CHARACTERS:
        return "That password repeats too few characters. Try a few unrelated words."
    if _is_a_run(lowered):
        return "That is a keyboard or number sequence, which is one of the first things guessed."
    if _is_common(password):
        return "That password is too common. Try a few unrelated words instead."
    if any(part in lowered for part in _personal_parts(email, name)):
        return "Don't use your name or email address in your password."
    return None


def require(password: str, *, email: str | None = None, name: str | None = None) -> None:
    problem = problem_with(password, email=email, name=name)
    if problem is not None:
        raise ValidationError(problem)
