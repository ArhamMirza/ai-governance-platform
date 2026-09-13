"""AI assistance: one place that talks to a model, on the org's chosen provider.

Two surfaces sit on top of this -- a per-field "draft this for me" button and
(next) a chat assistant -- so there is exactly one place where the provider is
chosen, one place the untrusted-content envelope is applied, one place tokens
are accounted for, and one place the read-and-draft-only boundary is enforced.

What this service will never do is change a record. It reads, and it returns
text for a person to look at. Saving, submitting, approving and advancing stay
where they already are: behind the permission and segregation-of-duties checks
in the services that own those decisions.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core import ai_prompting
from app.core.crypto import decrypt, encrypt
from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.core.impact_factors import IMPACT_FACTORS
from app.models.ai_assist import AiAssistSettings, AiProvider, AiUsage
from app.repositories import ai_assist_repository
from app.schemas.ai_assist import (
    AiAssistSettingsRead,
    AiAssistSettingsUpdate,
    AiAssistStatus,
    DraftResponse,
)

ENTITY_TYPE = "AiAssistSettings"

# How many characters of any single untrusted field reach the model. Long
# enough for real context, short enough that one enormous pasted field can't
# swallow the whole prompt budget.
MAX_FIELD_CHARS = 4_000
MAX_OUTPUT_TOKENS = 900


# ---------- settings ----------


def _defaults() -> AiAssistSettings:
    return AiAssistSettings(provider=AiProvider.ANTHROPIC, model="", daily_token_budget=200_000)


def _row(db: Session) -> AiAssistSettings:
    return ai_assist_repository.get_settings_row(db) or _defaults()


def get_settings(db: Session) -> AiAssistSettingsRead:
    row = _row(db)
    return AiAssistSettingsRead(
        provider=row.provider,
        model=row.model,
        fast_model=row.fast_model,
        base_url=row.base_url,
        daily_token_budget=row.daily_token_budget,
        has_api_key=bool(row.api_key_encrypted),
        updated_at=row.updated_at if row.id else None,
    )


def update_settings(
    db: Session, data: AiAssistSettingsUpdate, actor_id: int | None
) -> AiAssistSettingsRead:
    from app.services import audit_service

    if data.provider not in set(AiProvider):
        raise ValidationError(f"Unknown provider: {data.provider}")
    if not data.model.strip():
        raise ValidationError("Name the model to use.")
    if data.provider == AiProvider.LOCAL and not (data.base_url or "").strip():
        raise ValidationError(
            "A self-hosted model needs the URL it's served from, e.g. http://localhost:11434"
        )

    row = ai_assist_repository.get_settings_row(db)
    creating = row is None
    if row is None:
        row = _defaults()

    row.provider = data.provider
    row.model = data.model.strip()
    row.fast_model = (data.fast_model or "").strip() or None
    row.base_url = (data.base_url or "").strip() or None
    row.daily_token_budget = data.daily_token_budget
    # Omitted means "leave the stored key alone" -- the form can't show it,
    # so a blank field on save must not be read as "delete it". An explicit
    # empty string is how you actually clear it.
    if data.api_key is not None:
        row.api_key_encrypted = encrypt(data.api_key) if data.api_key.strip() else None

    row = (
        ai_assist_repository.create_settings(db, row)
        if creating
        else ai_assist_repository.save_settings(db, row)
    )
    # The key itself is never logged -- only that the configuration changed.
    audit_service.log(
        db, ENTITY_TYPE, row.id, "updated", actor_id,
        {"provider": row.provider, "model": row.model},
    )
    return get_settings(db)


def _unavailable_reason(row: AiAssistSettings) -> str | None:
    if not row.model.strip():
        return "No model configured yet."
    if row.daily_token_budget <= 0:
        return "AI assistance is switched off (the daily token budget is zero)."
    if row.provider == AiProvider.LOCAL:
        return None if row.base_url else "No URL set for the self-hosted model."
    return None if row.api_key_encrypted else "No API key set for this provider."


def is_available(db: Session) -> bool:
    return _unavailable_reason(_row(db)) is None


def status(db: Session) -> AiAssistStatus:
    row = _row(db)
    reason = _unavailable_reason(row)
    return AiAssistStatus(
        available=reason is None,
        provider=row.provider if row.id else None,
        model=row.model or None,
        is_local=row.provider == AiProvider.LOCAL,
        reason=reason,
    )


# ---------- talking to the model ----------


def _model_string(row: AiAssistSettings) -> str:
    """The provider-qualified name LiteLLM routes on.

    The one place provider-specific naming is known -- everything upstream
    deals in "the configured model".
    """
    if row.provider == AiProvider.LOCAL:
        # Served through LiteLLM's OpenAI-compatible path against the org's
        # own base_url, which covers Ollama, vLLM and LM Studio alike.
        return f"openai/{row.model}"
    return f"{row.provider}/{row.model}"


def _complete(
    db: Session,
    *,
    system: str,
    messages: list[dict],
    feature: str,
    actor_id: int | None,
    max_tokens: int = MAX_OUTPUT_TOKENS,
) -> str:
    """One model call, budgeted and accounted for."""
    row = _row(db)
    reason = _unavailable_reason(row)
    if reason is not None:
        raise ServiceUnavailableError(f"AI assistance isn't set up. {reason}")

    spent = ai_assist_repository.tokens_used_today(db, actor_id)
    if spent >= row.daily_token_budget:
        raise ServiceUnavailableError(
            f"You've used this deployment's daily AI budget ({row.daily_token_budget:,} "
            "tokens). It refreshes 24 hours after each use, or an admin can raise it."
        )

    # Imported here rather than at module scope: litellm is slow to import,
    # and an app whose operator never turns AI on shouldn't pay that on every
    # start.
    from litellm import completion

    kwargs: dict = {
        "model": _model_string(row),
        "messages": [{"role": "system", "content": system}, *messages],
        "max_tokens": max_tokens,
        # Low, not zero: this drafts governance text, where a predictable,
        # conservative register beats variety.
        "temperature": 0.3,
    }
    api_key = decrypt(row.api_key_encrypted) if row.api_key_encrypted else None
    if api_key:
        kwargs["api_key"] = api_key
    if row.base_url:
        kwargs["api_base"] = row.base_url

    try:
        response = completion(**kwargs)
    except Exception as exc:  # noqa: BLE001 -- every provider raises its own
        # The provider's own error text can carry the key or internal URLs,
        # so it is deliberately not passed through to the caller.
        raise ServiceUnavailableError(
            f"The {row.provider} model couldn't be reached. Check the provider "
            "settings, or try again."
        ) from exc

    usage = getattr(response, "usage", None)
    ai_assist_repository.record_usage(
        db,
        AiUsage(
            user_id=actor_id,
            feature=feature,
            provider=row.provider,
            model=row.model,
            prompt_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            completion_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
            created_at=datetime.now(UTC),
        ),
    )
    return (response.choices[0].message.content or "").strip()


# ---------- drafting ----------

# kind -> (what to call it to the user, what the model is being asked for).
# Narrative kinds are named for the ImpactAssessment column they fill.
_NARRATIVE_KINDS: dict[str, tuple[str, str]] = {
    "system_description": (
        "System Description",
        "a factual description of what this AI system is and how it works",
    ),
    "intended_purpose": (
        "Intended Purpose",
        "what this system is for: the decisions it supports and the outcome it exists to produce",
    ),
    "foreseeable_misuse": (
        "Foreseeable Misuse",
        "realistic ways this system could be misused or relied on beyond what it can support",
    ),
    "data_and_model_info": (
        "Data & Model Information",
        "the data this system is built on and the nature of the model itself",
    ),
    "deployment_environment": (
        "Deployment Environment",
        "where and how this system runs, and what it is connected to",
    ),
    "affected_interested_parties": (
        "Affected Interested Parties",
        "who is affected by this system -- including people who never interact with it directly",
    ),
    "human_oversight_role": (
        "Role of Human Oversight",
        "how a person oversees this system in practice: what they see, and what they can change",
    ),
    "conclusion": (
        "Conclusion",
        "a short conclusion on this system's overall impact, consistent with the factors scored",
    ),
}

_FACTOR_KINDS: dict[str, tuple[str, str]] = {
    "impact_factor_benefits": (
        "Benefits",
        "the concrete benefits this system offers in respect of this one impact factor",
    ),
    "impact_factor_harms": (
        "Harms",
        "the plausible harms this system could cause in respect of this one impact factor",
    ),
    "impact_factor_criteria": (
        "Scoring criteria",
        "what would justify each score from 1 to 5 for this one impact factor on this system",
    ),
}

DRAFT_KINDS = {**_NARRATIVE_KINDS, **_FACTOR_KINDS}


def _clip(value: object) -> str:
    text = str(value or "").strip()
    return text[:MAX_FIELD_CHARS] + " [...]" if len(text) > MAX_FIELD_CHARS else text


def _instruction(context_note: str, asked_for: str, envelopes: list[str]) -> str:
    joined = "\n".join(envelopes)
    return (
        f"{context_note}\n\n"
        f"Write {asked_for}.\n\n"
        "Ground every statement in the records quoted below. Where they don't say "
        "enough, write what they do support and name the gap in a final line "
        'beginning "Still needed:" -- an assessor would rather see an honest gap '
        "than a confident invention.\n\n"
        "Return only the drafted text: no preamble, no headings, no bullet-point "
        "scaffolding unless the content genuinely is a list. Aim for a short "
        "paragraph or two, in the plain professional register of an audit "
        f"document.\n\n{joined}"
    )


def draft_field(
    db: Session,
    *,
    kind: str,
    impact_assessment_id: int,
    factor: str | None,
    actor_id: int | None,
) -> DraftResponse:
    """Draft one field of an impact assessment, from what the record says.

    Returns text. Saves nothing: the caller hands it to the person who asked,
    in the same box their own typing goes, and it is theirs to keep, edit or
    discard.
    """
    from app.repositories import sheet_repository
    from app.services import impact_assessment_service

    if kind not in DRAFT_KINDS:
        raise ValidationError(f"Nothing to draft for '{kind}'.")
    if kind in _FACTOR_KINDS and factor not in IMPACT_FACTORS:
        raise ValidationError("That impact factor isn't one this assessment scores.")

    assessment = impact_assessment_service.get(db, impact_assessment_id)
    row = sheet_repository.get_row(db, assessment.ai_system_row_id)
    system_fields = dict(row.data) if row is not None else {}

    nonce = ai_prompting.new_nonce()
    label, asked_for = DRAFT_KINDS[kind]

    envelopes = [
        ai_prompting.wrap_record(
            {
                "Name": _clip(system_fields.get("name")),
                "Description": _clip(system_fields.get("description")),
                "Purpose": _clip(system_fields.get("purpose")),
                "Risk tier": _clip(system_fields.get("risk_tier")),
                "Data resources": _clip(system_fields.get("data_resources")),
                "Deployment/hosting": _clip(system_fields.get("hosting_environment")),
                "Human oversight roles": _clip(system_fields.get("oversight_roles")),
            },
            nonce,
            label="AI system inventory record",
            entity=f"AISystem {assessment.ai_system_row_id}",
        )
    ]

    if kind in _FACTOR_KINDS:
        scored = next(
            (
                f
                for f in impact_assessment_service.get_factors(db, impact_assessment_id)
                if f.factor == factor
            ),
            None,
        )
        envelopes.append(
            ai_prompting.wrap_record(
                {
                    "Benefits": _clip(scored.benefits if scored else ""),
                    "Harms": _clip(scored.harms if scored else ""),
                    "Scoring criteria": _clip(scored.criteria if scored else ""),
                },
                nonce,
                label=f"what this assessment already records for the {factor} factor",
            )
        )
        context_note = (
            f"You are drafting the {label} text for the single impact factor "
            f'"{factor}" of an ISO/IEC 42005 impact assessment.'
        )
    else:
        # The other narrative sections, so the draft is consistent with what
        # the assessment already says rather than contradicting it.
        others = {
            other_label: _clip(getattr(assessment, other_kind, ""))
            for other_kind, (other_label, _) in _NARRATIVE_KINDS.items()
            if other_kind != kind
        }
        envelopes.append(
            ai_prompting.wrap_record(
                others, nonce, label="what this assessment already records"
            )
        )
        context_note = (
            f"You are drafting the {label} section of an ISO/IEC 42005 impact assessment."
        )

    findings = sorted(
        {f for envelope in envelopes for f in ai_prompting.scan_for_injection(envelope)}
    )

    draft = _complete(
        db,
        system=ai_prompting.system_rules(nonce),
        messages=[{"role": "user", "content": _instruction(context_note, asked_for, envelopes)}],
        feature="draft_field",
        actor_id=actor_id,
    )
    return DraftResponse(draft=draft, injection_findings=findings)
