"""Measuring where the AI tokens go: reading each provider's usage, logging it,
and adding it up."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core import token_usage
from app.models.ai_assist import AiUsage
from app.models.user import User, UserRole
from app.schemas.ai_assist import AiAssistSettingsUpdate
from app.services import ai_assist_service, ai_spend_service

# ---------- reading a provider's usage ----------


def test_openai_style_usage_reports_cached_tokens_inside_prompt_details() -> None:
    usage = SimpleNamespace(
        prompt_tokens=1200,
        completion_tokens=80,
        prompt_tokens_details=SimpleNamespace(cached_tokens=1024),
    )

    assert token_usage.read(usage) == token_usage.TokenCounts(1200, 80, 1024, 0)


def test_anthropic_style_usage_reports_cache_reads_and_writes_separately() -> None:
    usage = SimpleNamespace(
        prompt_tokens=1500,
        completion_tokens=60,
        cache_read_input_tokens=1100,
        cache_creation_input_tokens=300,
    )

    assert token_usage.read(usage) == token_usage.TokenCounts(1500, 60, 1100, 300)


def test_usage_can_be_a_plain_dict() -> None:
    usage = {
        "prompt_tokens": 90,
        "completion_tokens": 10,
        "prompt_tokens_details": {"cached_tokens": 64},
    }

    assert token_usage.read(usage) == token_usage.TokenCounts(90, 10, 64, 0)


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        SimpleNamespace(),
        SimpleNamespace(prompt_tokens=None, completion_tokens="not a number"),
        SimpleNamespace(prompt_tokens=-5, completion_tokens=-1),
    ],
)
def test_a_provider_that_says_nothing_yields_zeros_not_an_error(usage) -> None:
    counts = token_usage.read(usage)

    assert counts.cache_read == counts.cache_write == 0
    assert counts.prompt >= 0 and counts.completion >= 0


# ---------- logging it ----------


def response(**usage_fields):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="An answer."))],
        usage=SimpleNamespace(**usage_fields),
    )


@pytest.fixture()
def configured(db_session: Session) -> Session:
    ai_assist_service.update_settings(
        db_session,
        AiAssistSettingsUpdate(
            provider="anthropic",
            model="claude-sonnet-5",
            api_key="sk-test",
            daily_token_budget=5_000_000,
        ),
        actor_id=None,
    )
    return db_session


def test_every_call_logs_what_was_cached(configured: Session) -> None:
    reply = response(
        prompt_tokens=1500,
        completion_tokens=60,
        cache_read_input_tokens=1100,
        cache_creation_input_tokens=300,
    )
    with patch("litellm.completion", return_value=reply):
        ai_assist_service._complete(
            configured,
            system="rules",
            messages=[{"role": "user", "content": "hi"}],
            feature="assistant",
            actor_id=None,
        )

    row = configured.query(AiUsage).one()
    assert (row.prompt_tokens, row.completion_tokens) == (1500, 60)
    assert (row.cache_read_tokens, row.cache_write_tokens) == (1100, 300)


def test_the_daily_budget_still_counts_prompt_plus_completion_only(configured: Session) -> None:
    configured.add(
        AiUsage(
            feature="assistant",
            provider="anthropic",
            model="m",
            prompt_tokens=1000,
            completion_tokens=100,
            cache_read_tokens=900,
            cache_write_tokens=50,
        )
    )
    configured.commit()

    from app.repositories import ai_assist_repository

    assert ai_assist_repository.tokens_used_today(configured, None) == 1100


# ---------- adding it up ----------


def add(db: Session, feature: str, prompt: int, completion: int, read=0, write=0, days_ago=0):
    db.add(
        AiUsage(
            feature=feature,
            provider="anthropic",
            model="m",
            prompt_tokens=prompt,
            completion_tokens=completion,
            cache_read_tokens=read,
            cache_write_tokens=write,
            created_at=datetime.now(UTC) - timedelta(days=days_ago, minutes=1),
        )
    )


def test_the_report_adds_up_by_feature_costliest_first(db_session: Session) -> None:
    add(db_session, "assistant", 2000, 200, read=1000)
    add(db_session, "assistant", 2200, 300, read=1100, write=100)
    add(db_session, "assistant_retry", 2400, 150)
    add(db_session, "policy_draft", 6000, 900)
    db_session.commit()

    report = ai_spend_service.report(db_session, days=30)

    assert [f.feature for f in report.by_feature] == [
        "policy_draft",
        "assistant",
        "assistant_retry",
    ]
    assistant = next(f for f in report.by_feature if f.feature == "assistant")
    assert (assistant.calls, assistant.prompt_tokens, assistant.completion_tokens) == (2, 4200, 500)
    assert (assistant.average_prompt_tokens, assistant.average_completion_tokens) == (2100, 250)
    assert (assistant.cache_read_tokens, assistant.cache_write_tokens) == (2100, 100)
    assert assistant.cache_hit_rate == 0.5
    assert report.calls == 4
    assert report.prompt_tokens == 12600
    assert report.cache_read_tokens == 2100
    assert report.cache_hit_rate == round(2100 / 12600, 4)


def test_an_empty_log_reports_zeros(db_session: Session) -> None:
    report = ai_spend_service.report(db_session)

    assert (report.calls, report.prompt_tokens, report.cache_hit_rate) == (0, 0, 0.0)
    assert report.by_feature == [] and report.by_day == []


def test_only_the_period_asked_for_is_counted_and_days_are_listed_in_order(
    db_session: Session,
) -> None:
    add(db_session, "assistant", 100, 10, days_ago=0)
    add(db_session, "assistant", 200, 20, days_ago=2)
    add(db_session, "assistant", 9999, 99, days_ago=40)
    db_session.commit()

    week = ai_spend_service.report(db_session, days=7)
    quarter = ai_spend_service.report(db_session, days=90)

    assert (week.calls, week.prompt_tokens) == (2, 300)
    assert quarter.calls == 3
    assert [d.tokens for d in week.by_day] == [220, 110]
    assert week.by_day[0].day < week.by_day[1].day


def test_a_feature_with_no_cache_reports_a_zero_rate_not_a_division_error(
    db_session: Session,
) -> None:
    add(db_session, "assistant_query", 0, 0)
    db_session.commit()

    assert ai_spend_service.report(db_session).by_feature[0].cache_hit_rate == 0.0


# ---------- who can see it ----------


def test_only_an_administrator_sees_the_spend(
    client: TestClient, test_user: User, db_session: Session, make_user, login_as
) -> None:
    add(db_session, "assistant", 100, 10)
    db_session.commit()

    body = client.get("/api/v1/ai-assist/spend").json()
    assert body["calls"] == 1 and body["by_feature"][0]["feature"] == "assistant"
    assert client.get("/api/v1/ai-assist/spend", params={"days": 0}).status_code == 422

    login_as(make_user(role=UserRole.VIEWER))
    assert client.get("/api/v1/ai-assist/spend").status_code == 403
