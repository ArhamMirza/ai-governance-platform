"""What the assistant would send for a set of questions, without calling a model.

    python -m app.prompt_report                      # a few sample questions
    python -m app.prompt_report --questions q.txt    # your own, one per line
    python -m app.prompt_report --json > before.json # to compare after a change

For each question it runs the real search and builds the real prompt, then
reports the size of each part and which records were found. It spends no tokens
and needs no AI provider: the point is to see where a prompt's size comes from,
and to compare two versions of the code on the same questions. Sizes are
estimates (characters / 4), good for comparing, not for billing; real counts are
on the Settings page once the assistant has been used.

The "found" list is what makes a cost change safe to judge: a change that makes
a prompt smaller by no longer finding the right record has made it worse.
"""

import argparse
import json
import sys
from pathlib import Path

from app.core import agent_tools, ai_prompting
from app.core.chunking import estimate_tokens

SAMPLE_QUESTIONS = [
    "Who approves new AI systems?",
    "What is our policy on using generative AI tools?",
    "Which AI systems have no impact assessment?",
    "How do we handle an AI incident?",
    "What are our obligations under the EU AI Act?",
    "Who is responsible for risk treatment?",
]


def measure(db, question: str) -> dict:
    # Imported here: the service pulls in the whole retrieval stack.
    from app.services import assistant_service, retrieval_service

    found = retrieval_service.search(db, question, limit=assistant_service.MAX_SOURCES)
    sources = assistant_service._number_sources([], found.citations)
    retrieved = list(sources)
    sources.extend(assistant_service._pinned_sources(db, len(sources) + 1))
    nonce = ai_prompting.new_nonce()
    turn = assistant_service._turn_message(
        nonce, question, sources, found.coverage_gaps, [], None, None
    )

    def size(group) -> int:
        return sum(estimate_tokens(assistant_service._source_envelope(nonce, s)) for s in group)

    pinned = [s for s in sources if s.citation.source == "pinned"]
    system = estimate_tokens(ai_prompting.CHAT_SYSTEM_RULES)
    tools = estimate_tokens(json.dumps(agent_tools.TOOL_SPECS))
    turn_tokens = estimate_tokens(turn)
    return {
        "question": question,
        "search_mode": found.mode,
        "tokens": {
            "system_rules": system,
            "tool_definitions": tools,
            "pinned_context": size(pinned),
            "retrieved_passages": size(retrieved),
            "whole_turn": turn_tokens,
            "first_call_total": system + tools + turn_tokens,
        },
        "found": [
            f"{s.citation.source_title}"
            + (f" / {s.citation.section}" if s.citation.section else "")
            for s in retrieved
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.prompt_report", description=__doc__.split("\n")[0]
    )
    parser.add_argument("--questions", help="A text file with one question per line.")
    parser.add_argument("--json", action="store_true", help="Print JSON, to compare two runs.")
    args = parser.parse_args(argv)

    if args.questions:
        questions = [
            line.strip()
            for line in Path(args.questions).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        questions = SAMPLE_QUESTIONS
    if not questions:
        print("No questions to measure.", file=sys.stderr)
        return 1

    from app.core.database import SessionLocal

    with SessionLocal() as db:
        results = [measure(db, q) for q in questions]

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print(f"{'first call':>10}  {'pinned':>6}  {'passages':>8}  {'found':>5}  question")
    for r in results:
        t = r["tokens"]
        print(
            f"{t['first_call_total']:>10}  {t['pinned_context']:>6}  {t['retrieved_passages']:>8}  "
            f"{len(r['found']):>5}  {r['question']}"
        )
    count = len(results)
    average = sum(r["tokens"]["first_call_total"] for r in results) // count
    print(f"\nAverage first call: about {average:,} input tokens (estimated, characters / 4).")
    fixed = results[0]["tokens"]
    print(
        f"Fixed every turn: system rules {fixed['system_rules']:,}, tool definitions "
        f"{fixed['tool_definitions']:,}, pinned context {fixed['pinned_context']:,}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
