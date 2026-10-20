"""How the organization's AI-use controls are configured, what the browser
extension is told, and the counts it reports back.

Metadata only, by design: an event is "this person, this day, this AI site,
this kind of thing, this many times". Never a page, a title, the time of day
or any text -- and only for sites in the AI tool catalogue, so the extension
can't be used to build a browsing history. See AgentEvent (the schema refuses
any other field) and record_events (it refuses any other site).
"""

import hashlib
import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core import agent_key, ai_tool_domains
from app.core.attempt_limiter import AttemptLimiter
from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.models.ai_dlp import (
    AIAgentCheckin,
    AIUsageAction,
    AIUsageEvent,
    AIUsageEventType,
    AIUseSettings,
    DLPAction,
)
from app.repositories import ai_use_repository, user_repository
from app.schemas.ai_use import (
    AgentCheckin,
    AgentEvents,
    AgentPolicy,
    AgentRule,
    AgentTool,
    AIUseSettingsUpdate,
    CoveragePerson,
    CoverageRead,
    UsageByDay,
    UsageByDomain,
    UsageByRule,
    UsageByType,
    UsageByUser,
    UsageSummary,
)
from app.services import ai_tool_service, audit_service, dlp_rule_service

ENTITY_TYPE = "AIUseSettings"
DEFAULT_RETENTION_DAYS = 90
# An extension's clock may be a day out, and a laptop that was shut over a
# weekend reports Friday's counts on Monday -- but nothing from the future.
FUTURE_TOLERANCE_DAYS = 1

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Wrong keys are counted per caller address, so a stranger who finds the
# endpoint can't walk the key space.
_key_limiter = AttemptLimiter(
    max_failures=10,
    window=timedelta(minutes=15),
    message="Too many wrong keys. Wait fifteen minutes and try again.",
)


def reset_key_limits() -> None:
    _key_limiter.reset()


def _today(today: date | None) -> date:
    return today if today is not None else datetime.now(UTC).date()


# ---------- settings ----------


def get_settings(db: Session) -> AIUseSettings:
    """The one settings row, provisioned (with its defaults) on first use."""
    settings = ai_use_repository.get_settings(db)
    if settings is None:
        settings = ai_use_repository.create_settings(
            db,
            AIUseSettings(
                unapproved_site_action=DLPAction.BLOCK, retention_days=DEFAULT_RETENTION_DAYS
            ),
        )
    return settings


def settings_or_default(db: Session) -> AIUseSettings:
    """The settings if they've been saved, else the defaults -- without
    writing a row, for the dashboard, compliance and the staff notice."""
    return ai_use_repository.get_settings(db) or AIUseSettings(
        unapproved_site_action=DLPAction.BLOCK, retention_days=DEFAULT_RETENTION_DAYS
    )


def update_settings(db: Session, data: AIUseSettingsUpdate, actor_id: int | None) -> AIUseSettings:
    settings = get_settings(db)
    changes = data.model_dump(exclude_unset=True)
    for required in ("unapproved_site_action", "retention_days"):
        if required in changes and changes[required] is None:
            raise ValidationError("That setting needs a value.")
    if "staff_notice" in changes:
        changes["staff_notice"] = (changes["staff_notice"] or "").strip() or None
    for field, value in changes.items():
        setattr(settings, field, value)
    settings = ai_use_repository.save_settings(db, settings)
    audit_service.log(
        db,
        ENTITY_TYPE,
        settings.id,
        "updated",
        actor_id,
        # The notice is long prose; the audit trail records that it changed.
        {k: ("(changed)" if k == "staff_notice" else v) for k, v in changes.items()},
    )
    if "retention_days" in changes:
        purge_expired(db)
    return settings


def rotate_enrollment_key(
    db: Session, actor_id: int | None, today: date | None = None
) -> tuple[str, str]:
    """Issues a new key, replacing (and so revoking) any earlier one. Returns
    the key and its hint; this is the only time the key exists in the clear."""
    settings = get_settings(db)
    key = agent_key.new_enrollment_key()
    settings.enrollment_key_hash = agent_key.hash_key(key)
    settings.enrollment_key_hint = agent_key.hint(key)
    settings.enrollment_key_created_on = _today(today)
    ai_use_repository.save_settings(db, settings)
    audit_service.log(
        db,
        ENTITY_TYPE,
        settings.id,
        "enrollment_key_rotated",
        actor_id,
        {"hint": settings.enrollment_key_hint},
    )
    return key, settings.enrollment_key_hint or ""


# ---------- the extension ----------


def authenticate_agent(db: Session, presented: str | None, caller: str) -> None:
    """Raises AuthenticationError unless `presented` is the current key. Wrong
    guesses from one caller are counted and, past a handful, refused outright
    (RateLimitedError) even for the right key."""
    _key_limiter.check(caller)
    settings = ai_use_repository.get_settings(db)
    stored = settings.enrollment_key_hash if settings else None
    if not presented or not agent_key.key_matches(presented, stored):
        _key_limiter.record_failure(caller)
        raise AuthenticationError("Invalid enrollment key")


def build_policy(db: Session) -> AgentPolicy:
    settings = settings_or_default(db)
    return AgentPolicy(
        unapproved_site_action=settings.unapproved_site_action,
        staff_notice=settings.staff_notice,
        tools=[
            AgentTool(
                name=tool.name,
                domains=tool.domains,
                status=tool.status,
                max_data_classification=tool.max_data_classification,
            )
            for tool in ai_tool_service.list_tools(db)
        ],
        rules=[
            AgentRule.model_validate(rule, from_attributes=True)
            for rule in dlp_rule_service.list_rules(db)
            if rule.enabled
        ],
    )


def policy_etag(policy: AgentPolicy) -> str:
    """Changes exactly when something the extension is told changes."""
    canonical = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return '"' + hashlib.sha256(canonical.encode()).hexdigest()[:32] + '"'


def _canonical_domain(db: Session, host: str) -> str:
    """The catalogue domain a host belongs to. Anything not an AI tool the
    organization has catalogued is refused: no other site is ever recorded."""
    normalised = ai_tool_domains.normalize_domain(host)
    tool = ai_tool_service.tool_for_host(db, normalised)
    if tool is None:
        raise ValidationError(f"{normalised} isn't a catalogued AI site, so it isn't recorded.")
    matching = [d for d in tool.domains if ai_tool_domains.host_matches(normalised, d)]
    return max(matching, key=len)


def record_events(db: Session, data: AgentEvents, today: date | None = None) -> int:
    """Adds a batch of counts, summing into any matching row so a retry or a
    second device doesn't double-count a row into two. All or nothing: one
    bad event refuses the batch. Returns how many events were accepted."""
    reference = _today(today)
    settings = settings_or_default(db)
    email = data.user_email.strip().lower()
    if not _EMAIL.match(email):
        raise ValidationError("user_email must be an email address.")
    earliest = reference - timedelta(days=settings.retention_days)
    latest = reference + timedelta(days=FUTURE_TOLERANCE_DAYS)
    known_rules = {rule.id for rule in dlp_rule_service.list_rules(db)}

    prepared = []
    for event in data.events:
        if not earliest <= event.day <= latest:
            raise ValidationError(f"{event.day} is outside the period counts are kept for.")
        is_dlp = event.event_type == AIUsageEventType.DLP_MATCH
        if is_dlp and event.rule_id is None:
            raise ValidationError("A DLP match must say which rule matched.")
        if not is_dlp and event.rule_id is not None:
            raise ValidationError("Only a DLP match has a rule.")
        if event.rule_id is not None and event.rule_id not in known_rules:
            raise NotFoundError("DLPRule", event.rule_id)
        prepared.append((event, _canonical_domain(db, event.domain)))

    for event, domain in prepared:
        key = {
            "user_ref": email,
            "day": event.day,
            "domain": domain,
            "event_type": event.event_type,
            "rule_id": event.rule_id,
            "action": event.action,
        }
        existing = ai_use_repository.find_event(db, **key)
        if existing is not None:
            existing.count += event.count
        else:
            ai_use_repository.add_event(db, AIUsageEvent(**key, count=event.count))
        # Flush so a second event in the same batch finds the first.
        db.flush()
    ai_use_repository.commit(db)
    purge_expired(db, reference)
    return len(prepared)


def record_checkin(db: Session, data: AgentCheckin, today: date | None = None) -> None:
    """Notes that this person's browser has reported in today. One row per
    person, overwritten each day -- so it is a roll call, not a log."""
    email = data.user_email.strip().lower()
    if not _EMAIL.match(email):
        raise ValidationError("user_email must be an email address.")
    reference = _today(today)
    existing = ai_use_repository.get_checkin(db, email)
    if existing is None:
        ai_use_repository.add_checkin(
            db,
            AIAgentCheckin(
                user_ref=email,
                first_seen=reference,
                last_seen=reference,
                extension_version=data.version,
            ),
        )
    else:
        existing.last_seen = max(existing.last_seen, reference)
        existing.extension_version = data.version
    ai_use_repository.commit(db)


def purge_expired(db: Session, today: date | None = None) -> int:
    """Deletes counts older than the retention period. Returns how many rows went."""
    settings = settings_or_default(db)
    cutoff = _today(today) - timedelta(days=settings.retention_days)
    return ai_use_repository.delete_events_before(db, cutoff)


# ---------- the usage dashboard ----------

_SITE_EVENTS = {AIUsageEventType.UNAPPROVED_SITE, AIUsageEventType.BLOCKED_SITE}


def week_counts(db: Session, today: date | None = None) -> tuple[int, int]:
    """(unapproved-site visits, DLP matches) in the last seven days, for the dashboard."""
    since = _today(today) - timedelta(days=6)
    sites = dlp = 0
    for event in ai_use_repository.list_events_since(db, since):
        if event.event_type in _SITE_EVENTS:
            sites += event.count
        elif event.event_type == AIUsageEventType.DLP_MATCH:
            dlp += event.count
    return sites, dlp


def week_overrides(db: Session, today: date | None = None) -> int:
    """Times someone clicked through a warning in the last seven days."""
    since = _today(today) - timedelta(days=6)
    return sum(
        event.count
        for event in ai_use_repository.list_events_since(db, since)
        if event.action == AIUsageAction.OVERRIDDEN
    )


def coverage(db: Session, days: int = 7, today: date | None = None) -> CoverageRead:
    """Who has reported in within the last `days` days, among everyone who has
    an active account (they are all expected to have the extension)."""
    reference = _today(today)
    since = reference - timedelta(days=days - 1)
    checkins = {c.user_ref: c for c in ai_use_repository.list_checkins(db)}
    active = [u for u in user_repository.list_all(db) if u.is_active]
    known = {u.email.lower() for u in active}

    people = []
    for user in active:
        checkin = checkins.get(user.email.lower())
        if checkin is None:
            status = "never"
        elif checkin.last_seen >= since:
            status = "reporting"
        else:
            status = "quiet"
        people.append(
            CoveragePerson(
                user_id=user.id,
                name=user.name,
                email=user.email,
                last_seen=checkin.last_seen if checkin else None,
                extension_version=checkin.extension_version if checkin else None,
                status=status,
            )
        )
    # Those who need attention first: never reported, then gone quiet, longest ago first.
    order = {"never": 0, "quiet": 1, "reporting": 2}
    people.sort(key=lambda p: (order[p.status], p.last_seen or date.min, p.name.lower()))
    return CoverageRead(
        days=days,
        active_people=len(people),
        reporting=sum(1 for p in people if p.status == "reporting"),
        people=people,
        unmatched_reporters=sum(
            1 for ref, c in checkins.items() if ref not in known and c.last_seen >= since
        ),
    )


def coverage_gap_count(db: Session, today: date | None = None) -> int:
    """People who have no recent report -- but only once a key has been issued,
    because before that the rollout hasn't started and nobody could report."""
    if settings_or_default(db).enrollment_key_hash is None:
        return 0
    result = coverage(db, 7, today)
    return result.active_people - result.reporting


def usage_summary(db: Session, days: int = 30, today: date | None = None) -> UsageSummary:
    reference = _today(today)
    events = ai_use_repository.list_events_since(db, reference - timedelta(days=days - 1))
    tools_by_domain = {d: t for t in ai_tool_service.list_tools(db) for d in t.domains}
    rules = {r.id: r.name for r in dlp_rule_service.list_rules(db)}
    names = {u.email.lower(): u.name for u in user_repository.list_all(db)}

    by_type: dict[str, int] = defaultdict(int)
    by_domain: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_rule: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_user: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_day: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    overrides = 0
    for e in events:
        by_type[e.event_type] += e.count
        if e.action == AIUsageAction.OVERRIDDEN:
            overrides += e.count
            by_domain[e.domain]["overrides"] += e.count
            by_user[e.user_ref]["overrides"] += e.count
        is_site = e.event_type in _SITE_EVENTS
        is_dlp = e.event_type == AIUsageEventType.DLP_MATCH
        if is_site:
            by_domain[e.domain]["unapproved"] += e.count
            by_user[e.user_ref]["unapproved"] += e.count
            by_day[e.day]["unapproved"] += e.count
        if e.event_type == AIUsageEventType.BLOCKED_SITE:
            by_domain[e.domain]["blocked"] += e.count
        if is_dlp:
            by_domain[e.domain]["dlp"] += e.count
            by_user[e.user_ref]["dlp"] += e.count
            by_day[e.day]["dlp"] += e.count
            if e.rule_id is not None:
                by_rule[e.rule_id]["matches"] += e.count
                if e.action == "blocked":
                    by_rule[e.rule_id]["blocked"] += e.count

    return UsageSummary(
        days=days,
        overrides=overrides,
        by_type=[UsageByType(event_type=k, count=v) for k, v in sorted(by_type.items())],
        by_domain=[
            UsageByDomain(
                domain=domain,
                tool_name=tools_by_domain[domain].name if domain in tools_by_domain else None,
                status=tools_by_domain[domain].status if domain in tools_by_domain else None,
                unapproved=c["unapproved"],
                blocked=c["blocked"],
                dlp_matches=c["dlp"],
                overrides=c["overrides"],
            )
            for domain, c in sorted(
                by_domain.items(), key=lambda i: -(i[1]["unapproved"] + i[1]["dlp"])
            )
        ],
        by_rule=[
            UsageByRule(
                rule_id=rule_id,
                rule_name=rules.get(rule_id),
                matches=c["matches"],
                blocked=c["blocked"],
            )
            for rule_id, c in sorted(by_rule.items(), key=lambda i: -i[1]["matches"])
        ],
        by_user=[
            UsageByUser(
                user_ref=ref,
                user_name=names.get(ref),
                unapproved=c["unapproved"],
                dlp_matches=c["dlp"],
                overrides=c["overrides"],
            )
            for ref, c in sorted(
                by_user.items(), key=lambda i: -(i[1]["unapproved"] + i[1]["dlp"])
            )[:20]
        ],
        by_day=[
            UsageByDay(day=day, unapproved=c["unapproved"], dlp_matches=c["dlp"])
            for day, c in sorted(by_day.items())
        ],
    )
