"""The prompt-size report: the real search and the real prompt, no model."""

import json

from sqlalchemy.orm import Session

from app import prompt_report


def test_it_sizes_each_part_of_the_prompt_and_lists_what_was_found(db_session: Session) -> None:
    from app.models.policy import Policy
    from app.services import document_index_service

    db_session.add(Policy(title="AI Policy", description="Sets the rules for using AI tools."))
    db_session.commit()
    document_index_service.drain(db_session, limit=None)

    result = prompt_report.measure(db_session, "What is the policy on using AI tools?")

    tokens = result["tokens"]
    assert tokens["system_rules"] > 0 and tokens["tool_definitions"] > 0
    assert tokens["first_call_total"] == (
        tokens["system_rules"] + tokens["tool_definitions"] + tokens["whole_turn"]
    )
    assert tokens["whole_turn"] >= tokens["pinned_context"] + tokens["retrieved_passages"]
    assert result["question"] == "What is the policy on using AI tools?"
    assert isinstance(result["found"], list)


def test_a_question_nothing_answers_finds_nothing_but_still_has_fixed_costs(
    db_session: Session,
) -> None:
    result = prompt_report.measure(db_session, "zzqx unrelated gibberish")

    assert result["found"] == []
    assert result["tokens"]["retrieved_passages"] == 0
    assert result["tokens"]["first_call_total"] > 0


def test_the_command_prints_a_table_or_json(
    db_session: Session, monkeypatch, capsys, tmp_path
) -> None:
    from contextlib import contextmanager

    @contextmanager
    def session():
        yield db_session

    monkeypatch.setattr("app.core.database.SessionLocal", session)
    questions = tmp_path / "q.txt"
    questions.write_text("Who approves AI systems?\n\nWhat is the policy?\n", encoding="utf-8")

    assert prompt_report.main(["--questions", str(questions)]) == 0
    table = capsys.readouterr().out
    assert "Who approves AI systems?" in table and "Average first call" in table

    assert prompt_report.main(["--questions", str(questions), "--json"]) == 0
    parsed = json.loads(capsys.readouterr().out)
    assert [r["question"] for r in parsed] == ["Who approves AI systems?", "What is the policy?"]


def test_an_empty_question_file_is_an_error(tmp_path, capsys) -> None:
    empty = tmp_path / "q.txt"
    empty.write_text("\n \n", encoding="utf-8")

    assert prompt_report.main(["--questions", str(empty)]) == 1
    assert "No questions" in capsys.readouterr().err
