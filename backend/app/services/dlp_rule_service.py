"""The data-loss-prevention rules the browser extension applies.

Ordinary edit permission, like the rest of the register: a rule is a policy
choice the governance team makes and revisits. What a rule may look for is
checked here (app.core.dlp_rules) because it runs on every employee's browser.
"""

from sqlalchemy.orm import Session

from app.core import dlp_rules
from app.core.exceptions import NotFoundError, ValidationError
from app.models.ai_dlp import DLPRule, DLPRuleKind
from app.repositories import ai_use_repository
from app.schemas.ai_use import DLPRuleCreate, DLPRuleUpdate
from app.services import audit_service, framework_service

ENTITY_TYPE = "DLPRule"


def _get_or_raise(db: Session, rule_id: int) -> DLPRule:
    rule = ai_use_repository.get_rule(db, rule_id)
    if rule is None:
        raise NotFoundError("DLPRule", rule_id)
    return rule


def _definition(kind: str, builtin_key, keywords, pattern) -> dict:
    """The one field a kind of rule uses, checked; the other two cleared so a
    rule never carries a stale definition from a form that was filled in and
    changed."""
    fields: dict = {"builtin_key": None, "keywords": None, "pattern": None}
    if kind == DLPRuleKind.BUILTIN:
        fields["builtin_key"] = dlp_rules.validate_builtin(builtin_key)
    elif kind == DLPRuleKind.KEYWORDS:
        fields["keywords"] = dlp_rules.validate_keywords(keywords)
    else:
        fields["pattern"] = dlp_rules.validate_pattern(pattern)
    return fields


def builtin_detectors() -> list[tuple[str, str, str]]:
    return [(key, label, text) for key, (label, text) in dlp_rules.BUILTIN_DETECTORS.items()]


def list_rules(db: Session) -> list[DLPRule]:
    return ai_use_repository.list_rules(db)


def get_rule(db: Session, rule_id: int) -> DLPRule:
    return _get_or_raise(db, rule_id)


def create_rule(db: Session, data: DLPRuleCreate, actor_id: int | None) -> DLPRule:
    fields = data.model_dump(exclude={"builtin_key", "keywords", "pattern"})
    fields.update(_definition(data.kind, data.builtin_key, data.keywords, data.pattern))
    rule = ai_use_repository.create_rule(db, DLPRule(**fields))
    audit_service.log(
        db,
        ENTITY_TYPE,
        rule.id,
        "created",
        actor_id,
        # The name and what kind of thing it looks for -- the definition itself
        # (which may name a client or a project) stays out of the audit log.
        {"name": rule.name, "kind": rule.kind, "action": rule.action},
    )
    return rule


def update_rule(db: Session, rule_id: int, data: DLPRuleUpdate, actor_id: int | None) -> DLPRule:
    rule = _get_or_raise(db, rule_id)
    changes = data.model_dump(exclude_unset=True)
    for required in ("name", "classification", "action", "enabled"):
        if required in changes and changes[required] is None:
            raise ValidationError(f"A rule needs its {required.replace('_', ' ')}.")
    definition_keys = {"builtin_key", "keywords", "pattern"} & changes.keys()
    if definition_keys:
        merged = {
            "builtin_key": rule.builtin_key,
            "keywords": rule.keywords,
            "pattern": rule.pattern,
        }
        merged.update({key: changes[key] for key in definition_keys})
        changes.update(_definition(rule.kind, **merged))
    for field, value in changes.items():
        setattr(rule, field, value)
    rule = ai_use_repository.save_rule(db, rule)
    audit_service.log(
        db,
        ENTITY_TYPE,
        rule.id,
        "updated",
        actor_id,
        {"fields": sorted(changes), "enabled": rule.enabled, "action": rule.action},
    )
    return rule


def delete_rule(db: Session, rule_id: int, actor_id: int | None) -> None:
    rule = _get_or_raise(db, rule_id)
    framework_service.delete_tags(db, ENTITY_TYPE, rule_id)
    ai_use_repository.delete_rule(db, rule)
    audit_service.log(db, ENTITY_TYPE, rule_id, "deleted", actor_id, {"name": rule.name})
