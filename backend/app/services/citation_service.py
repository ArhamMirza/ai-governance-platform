"""Checking what a model cites against what it was actually given.

Shared by everything that asks a model to ground text in retrieved sources
-- the chat assistant, and whole-record drafting. Kept in one place because
these are the rules that decide what a reader is shown as supported, and two
slightly different copies of them would mean two slightly different answers
to "did the model make this up?".
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_chunk import SourceType
from app.models.risk_assessment import RiskAssessment
from app.models.sheet import SheetRow

CITATION = re.compile(r"\[S(\d+)\]")
# An opening or closing envelope tag of any nonce. Stripped from anything a
# model wrote before it is shown or stored.
UNTRUSTED_TAG = re.compile(r"</?source_[0-9a-f]+[^>]*>", re.IGNORECASE)

# A sentence, with any citation markers that trail its full stop kept with it:
# "Kept 24 months. [S1]" is one sentence citing S1, not two. A full stop only
# ends a sentence when whitespace or the end of the line follows it, so
# "A.5.23", "v2.0" and "1.5 FTE" are not cut apart -- control references are
# the commonest thing in these answers and the worst thing to mangle. An
# abbreviation like "e.g." still reads as a boundary; that costs a stray
# fragment at worst, never a claim kept that should have gone.
_SENTENCE = re.compile(r"[^\n]*?(?:[.!?]+(?:\s*\[S\d+\])*(?=\s|$)|$)")


def cited_numbers(text: str) -> list[int]:
    """Source numbers cited inline, in order of first appearance."""
    seen: list[int] = []
    for match in CITATION.finditer(text):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def split_supported(cited: list[int], given: set[int]) -> tuple[list[int], list[int]]:
    """Cited numbers that were provided, and those that were invented."""
    return [n for n in cited if n in given], [n for n in cited if n not in given]


def strip_fabricated(answer: str, fabricated: list[int]) -> str:
    """Remove fabricated citations, and any claim that rested only on one.

    Deleting just the marker would leave the sentence standing, uncited, and
    still reading as a fact -- which is exactly the hallucination the check
    exists to catch. A sentence citing a real source as well as an invented
    one keeps its real support and loses only the invented marker.
    """
    bad = set(fabricated)

    def without_bad_markers(text: str) -> str:
        text = CITATION.sub(lambda m: "" if int(m.group(1)) in bad else m.group(0), text)
        # Close the gap a removed marker leaves: "the board [S9]." -> "the board."
        return re.sub(r"[ \t]+([.,;:!?])", r"\1", re.sub(r"[ \t]{2,}", " ", text))

    kept_lines = []
    for line in answer.split("\n"):
        kept = []
        for sentence in _SENTENCE.findall(line):
            if not sentence.strip():
                continue
            cited = {int(n) for n in CITATION.findall(sentence)}
            if cited and cited <= bad:
                continue
            kept.append(without_bad_markers(sentence))
        text = "".join(kept).strip()
        # A bullet whose only content was the removed claim goes with it.
        if re.fullmatch(r"([-*•]|\d+\.)?", text):
            text = ""
        kept_lines.append(text)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept_lines)).strip()


def without_markers(text: str) -> str:
    """Text with its [S#] markers removed, for places citations are listed
    separately rather than inline."""
    text = re.sub(r"[ \t]{2,}", " ", CITATION.sub("", text))
    return re.sub(r"[ \t]+([.,;:!?])", r"\1", text).strip()


def href_for(db: Session, entity_type: str, entity_id: int) -> str | None:
    """Where in the application a cited record can be opened."""
    if entity_type == SourceType.POLICY:
        return f"/policies/{entity_id}"
    if entity_type == SourceType.PROCEDURE:
        return f"/procedures/{entity_id}"
    if entity_type == SourceType.AI_SYSTEM:
        return f"/ai-systems/{entity_id}"
    if entity_type == SourceType.IMPACT_ASSESSMENT:
        return f"/impact-assessments/{entity_id}"
    if entity_type == SourceType.DATA_INVENTORY:
        return "/data-inventory"
    if entity_type == SourceType.RISK_ITEM:
        row = db.get(SheetRow, entity_id)
        assessment = (
            db.scalar(select(RiskAssessment).where(RiskAssessment.sheet_id == row.sheet_id))
            if row is not None
            else None
        )
        return f"/risk-assessments/{assessment.id}" if assessment else "/risk-assessments"
    return None
