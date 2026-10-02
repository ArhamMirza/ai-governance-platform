"""The organization's EU AI Act applicability assessment, and what it means
for each tracked article.

Per-article overrides reuse FrameworkSoaEntry: for an EU AI Act article, a
row means someone deliberately overrode the automatic answer, and no row
means "follow the assessment". (Annex A controls keep their own meaning --
every one has a row from its migration.)
"""

from sqlalchemy.orm import Session

from app.core import eu_ai_act_scope
from app.core.exceptions import NotFoundError, ValidationError
from app.models.eu_ai_act_applicability import EuAiActApplicability
from app.models.framework_control import Framework, FrameworkControl
from app.models.framework_soa_entry import FrameworkSoaEntry, SoaApplicability
from app.repositories import (
    eu_ai_act_repository,
    framework_control_repository,
    framework_soa_repository,
)
from app.schemas.eu_ai_act import (
    EuAiActApplicabilityRead,
    EuAiActApplicabilityUpdate,
    EuAiActArticleRead,
    EuAiActScope,
)
from app.services import ai_system_inventory_service, audit_service

ENTITY_TYPE = "EuAiActApplicability"
ENTITY_ID = 1
OVERRIDE_ENTITY_TYPE = "FrameworkSoaEntry"
OVERRIDE_ACTION = "eu_ai_act_override_set"
OVERRIDE_CLEARED_ACTION = "eu_ai_act_override_cleared"
HIGH_RISK_TIER = "high"


def get_settings(db: Session) -> EuAiActApplicability | None:
    return eu_ai_act_repository.get(db)


def scope_of(settings: EuAiActApplicability | None) -> EuAiActScope:
    if settings is None or settings.in_scope is None:
        return "not_assessed"
    return "in_scope" if settings.in_scope else "out_of_scope"


def high_risk_system_count(db: Session) -> int:
    return sum(
        1
        for row in ai_system_inventory_service.list_rows(db)
        if str(row.data.get("risk_tier") or "").strip().lower() == HIGH_RISK_TIER
    )


def read_settings(db: Session) -> EuAiActApplicabilityRead:
    settings = get_settings(db)
    return EuAiActApplicabilityRead(
        scope=scope_of(settings),
        in_scope=settings.in_scope if settings else None,
        scope_justification=settings.scope_justification if settings else None,
        is_provider=settings.is_provider if settings else False,
        is_deployer=settings.is_deployer if settings else False,
        is_importer=settings.is_importer if settings else False,
        is_distributor=settings.is_distributor if settings else False,
        has_high_risk_systems=settings.has_high_risk_systems if settings else None,
        high_risk_system_count=high_risk_system_count(db),
        updated_by=settings.updated_by if settings else None,
        updated_at=settings.updated_at if settings else None,
    )


def _validate(data: EuAiActApplicabilityUpdate) -> None:
    if data.in_scope is False and not (data.scope_justification or "").strip():
        raise ValidationError(
            "Record why the EU AI Act doesn't apply -- an unexplained exclusion is the "
            "first thing an auditor or regulator will ask about."
        )
    if data.in_scope:
        if not any((data.is_provider, data.is_deployer, data.is_importer, data.is_distributor)):
            raise ValidationError(
                "Choose at least one role your organization holds under the EU AI Act."
            )
        if data.has_high_risk_systems is None:
            raise ValidationError(
                "Say whether your organization provides or deploys any high-risk AI systems."
            )


def update_settings(
    db: Session, data: EuAiActApplicabilityUpdate, actor_id: int | None
) -> EuAiActApplicabilityRead:
    _validate(data)
    settings = get_settings(db)
    if settings is None:
        settings = eu_ai_act_repository.create(db, EuAiActApplicability(**data.model_dump()))
    else:
        for field, value in data.model_dump().items():
            setattr(settings, field, value)
    settings.updated_by = actor_id
    eu_ai_act_repository.save(db, settings)
    audit_service.log(db, ENTITY_TYPE, ENTITY_ID, "updated", actor_id, data.model_dump())
    return read_settings(db)


def effective_applicability(
    settings: EuAiActApplicability | None,
    code: str,
    override: FrameworkSoaEntry | None,
) -> tuple[bool, str]:
    """An override, if there is one, wins over the automatic answer."""
    if override is not None:
        applicable = override.applicability == SoaApplicability.APPLICABLE
        return applicable, f"Overridden: {override.justification}"
    return eu_ai_act_scope.automatic_applicability(settings, code)


def _articles(db: Session) -> list[FrameworkControl]:
    return framework_control_repository.list_all(db, framework=Framework.EU_AI_ACT)


def _get_article_or_raise(db: Session, control_id: int) -> FrameworkControl:
    control = framework_control_repository.get_by_id(db, control_id)
    if control is None or control.framework != Framework.EU_AI_ACT:
        raise NotFoundError("EU AI Act article", control_id)
    return control


def article_statuses(db: Session) -> list[EuAiActArticleRead]:
    settings = get_settings(db)
    overrides = {
        entry.framework_control_id: entry for entry in framework_soa_repository.list_all(db)
    }
    results = []
    for control in _articles(db):
        override = overrides.get(control.id)
        automatic, automatic_reason = eu_ai_act_scope.automatic_applicability(
            settings, control.code
        )
        applicable, reason = effective_applicability(settings, control.code, override)
        results.append(
            EuAiActArticleRead(
                id=control.id,
                code=control.code,
                title=control.title,
                automatic_applicable=automatic,
                automatic_reason=automatic_reason,
                override_applicability=override.applicability if override else None,
                override_justification=override.justification if override else None,
                applicable=applicable,
                reason=reason,
            )
        )
    return results


def set_override(
    db: Session,
    control_id: int,
    applicability: SoaApplicability,
    justification: str,
    actor_id: int | None,
) -> None:
    if not justification.strip():
        raise ValidationError(
            "Record why this article's applicability differs from the assessment."
        )
    _get_article_or_raise(db, control_id)
    framework_soa_repository.upsert(db, control_id, applicability, justification, actor_id)
    audit_service.log(
        db,
        OVERRIDE_ENTITY_TYPE,
        control_id,
        OVERRIDE_ACTION,
        actor_id,
        {"applicability": applicability, "justification": justification},
    )


def clear_override(db: Session, control_id: int, actor_id: int | None) -> None:
    _get_article_or_raise(db, control_id)
    entry = framework_soa_repository.get_by_control_id(db, control_id)
    if entry is None:
        return
    framework_soa_repository.delete(db, entry)
    audit_service.log(db, OVERRIDE_ENTITY_TYPE, control_id, OVERRIDE_CLEARED_ACTION, actor_id)
