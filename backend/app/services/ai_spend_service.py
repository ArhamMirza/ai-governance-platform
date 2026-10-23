"""Where the AI tokens go: totals from the usage log, by kind of call and by day.

The log already holds one row per model call (see AiUsage); this only adds up
what it holds. It is the measurement the cost work rests on -- before anything is
made cheaper, there should be a number to make smaller -- and a record, in a
platform whose job is governing AI, of how this deployment spends its own.
Aggregates only: nothing here says who asked or what about.
"""

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_assist import AiUsage
from app.schemas.ai_assist import AiSpendDay, AiSpendFeature, AiSpendReport


def _rate(cache_read: int, prompt: int) -> float:
    return round(cache_read / prompt, 4) if prompt else 0.0


def report(db: Session, days: int = 30, today: date | None = None) -> AiSpendReport:
    reference = today or datetime.now(UTC).date()
    since = datetime.combine(reference - timedelta(days=days - 1), datetime.min.time(), tzinfo=UTC)

    rows = db.execute(
        select(
            AiUsage.feature,
            func.count(),
            func.coalesce(func.sum(AiUsage.prompt_tokens), 0),
            func.coalesce(func.sum(AiUsage.completion_tokens), 0),
            func.coalesce(func.sum(AiUsage.cache_read_tokens), 0),
            func.coalesce(func.sum(AiUsage.cache_write_tokens), 0),
        )
        .where(AiUsage.created_at >= since)
        .group_by(AiUsage.feature)
    ).all()

    features = [
        AiSpendFeature(
            feature=feature,
            calls=calls,
            prompt_tokens=int(prompt),
            completion_tokens=int(completion),
            average_prompt_tokens=int(prompt) // calls,
            average_completion_tokens=int(completion) // calls,
            cache_read_tokens=int(read),
            cache_write_tokens=int(write),
            cache_hit_rate=_rate(int(read), int(prompt)),
        )
        for feature, calls, prompt, completion, read, write in rows
    ]
    # The costliest first: that is where to look.
    features.sort(key=lambda f: -(f.prompt_tokens + f.completion_tokens))

    per_day = db.execute(
        select(
            func.date(AiUsage.created_at),
            func.count(),
            func.coalesce(func.sum(AiUsage.prompt_tokens + AiUsage.completion_tokens), 0),
        )
        .where(AiUsage.created_at >= since)
        .group_by(func.date(AiUsage.created_at))
        .order_by(func.date(AiUsage.created_at))
    ).all()

    prompt = sum(f.prompt_tokens for f in features)
    read = sum(f.cache_read_tokens for f in features)
    return AiSpendReport(
        days=days,
        calls=sum(f.calls for f in features),
        prompt_tokens=prompt,
        completion_tokens=sum(f.completion_tokens for f in features),
        cache_read_tokens=read,
        cache_write_tokens=sum(f.cache_write_tokens for f in features),
        cache_hit_rate=_rate(read, prompt),
        by_feature=features,
        by_day=[
            AiSpendDay(day=_as_date(day), calls=calls, tokens=int(tokens))
            for day, calls, tokens in per_day
        ],
    )


def _as_date(value: object) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value))
