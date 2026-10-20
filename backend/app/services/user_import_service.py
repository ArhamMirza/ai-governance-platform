"""Creating and updating staff accounts from a CSV file.

Two steps, on purpose: a preview that changes nothing, then the import, which
works the file out again from scratch rather than trusting what the preview
said. Accounts are matched on email, so running the same file twice does
nothing the second time and a corrected file fixes the first.

What it will not do: make anyone an administrator, change an administrator,
change your own account, bring back a deactivated account, or deactivate
anybody. Those are decisions to take one at a time on the Users page; people
who are in the system but missing from the file are only listed.
"""

import csv
import io
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ValidationError
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.schemas.user import UserCreate
from app.schemas.user_import import (
    ImportAction,
    UserImportCreated,
    UserImportMissing,
    UserImportPreview,
    UserImportResult,
    UserImportRow,
)
from app.services import audit_service, auth_service, user_service

MAX_BYTES = 1_000_000
# Each new account costs a deliberately slow password hash, so a file is kept
# to a size that finishes in a reasonable time. Larger lists go in several files.
MAX_ROWS = 200

DEFAULT_ROLE = UserRole.EMPLOYEE
# What a file may grant. Administrators are created one at a time.
IMPORTABLE_ROLES = (UserRole.CONTRIBUTOR, UserRole.VIEWER, UserRole.EMPLOYEE)

_HEADERS = {
    "name": {"name", "full name", "fullname", "employee", "employee name"},
    "email": {"email", "e-mail", "email address", "work email"},
    "role": {"role", "access", "account type"},
}
# Domain labels exclude "." so the pattern has one way to match, not many.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")


@dataclass
class _Line:
    number: int
    name: str
    email: str
    role: str | None
    problem: str | None = None


@dataclass
class _Planned:
    line: _Line
    action: ImportAction
    note: str | None = None
    existing: User | None = None
    new_name: str | None = None
    new_role: str | None = None


def _decode(content: bytes) -> str:
    if not content.strip():
        raise ValidationError("That file is empty.")
    if len(content) > MAX_BYTES:
        raise ValidationError("That file is too large. Keep it under 1 MB.")
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError(
            "That file isn't plain text in UTF-8. In your spreadsheet choose Save as > CSV UTF-8."
        ) from error


def _delimiter(header_line: str) -> str:
    return max((",", ";", "\t"), key=header_line.count)


def _column(headers: list[str], key: str) -> int | None:
    for index, header in enumerate(headers):
        if header.strip().lower() in _HEADERS[key]:
            return index
    return None


def _parse(content: bytes) -> list[_Line]:
    text = _decode(content)
    reader = csv.reader(io.StringIO(text), delimiter=_delimiter(text.splitlines()[0]))
    try:
        headers = next(reader)
    except StopIteration as error:
        raise ValidationError("That file is empty.") from error
    name_at, email_at, role_at = (_column(headers, k) for k in ("name", "email", "role"))
    if name_at is None or email_at is None:
        raise ValidationError(
            "The first row must name its columns, and needs at least 'name' and 'email'. "
            "'role' is optional."
        )

    lines: list[_Line] = []
    for row in reader:
        number = reader.line_num
        if not any(cell.strip() for cell in row):
            continue
        if len(lines) >= MAX_ROWS:
            raise ValidationError(
                f"That file has more than {MAX_ROWS} people. Split it into smaller files."
            )

        def cell(index: int | None, row: list[str] = row) -> str:
            return row[index].strip() if index is not None and index < len(row) else ""

        lines.append(
            _Line(
                number=number,
                name=cell(name_at),
                email=cell(email_at).lower(),
                role=cell(role_at).lower() or None,
            )
        )
    if not lines:
        raise ValidationError("That file has a header row but no people.")
    return lines


def _problem(line: _Line, seen: dict[str, int]) -> str | None:
    if not line.name:
        return "No name."
    if len(line.name) > 200:
        return "The name is longer than 200 characters."
    if not line.email or len(line.email) > 320 or not _EMAIL.match(line.email):
        return "That is not an email address."
    if line.email in seen:
        return f"Appears twice in the file (first on line {seen[line.email]})."
    if line.role is not None:
        if line.role == UserRole.ADMIN:
            return "Administrators are created one at a time on the Users page."
        if line.role not in IMPORTABLE_ROLES:
            allowed = ", ".join(IMPORTABLE_ROLES)
            return f"Unknown role '{line.role}'. Use {allowed}, or leave it blank."
    return None


def _plan(db: Session, content: bytes, actor: User) -> list[_Planned]:
    lines = _parse(content)
    existing = {u.email.lower(): u for u in user_repository.list_all(db)}
    seen: dict[str, int] = {}
    plan: list[_Planned] = []
    for line in lines:
        problem = _problem(line, seen)
        seen.setdefault(line.email, line.number)
        if problem is not None:
            plan.append(_Planned(line, "skip", problem))
            continue
        role = line.role or None
        user = existing.get(line.email)
        if user is None:
            plan.append(_Planned(line, "create", new_role=role or DEFAULT_ROLE))
            continue
        if not user.is_active:
            plan.append(
                _Planned(line, "skip", "Deactivated. Reactivate it on the Users page if needed.")
            )
            continue
        if user.id == actor.id:
            plan.append(_Planned(line, "skip", "That is your own account."))
            continue
        if user.role == UserRole.ADMIN:
            plan.append(_Planned(line, "skip", "An administrator; change those on the Users page."))
            continue
        changes = []
        new_name = line.name if line.name != user.name else None
        # A blank role leaves the person's current one alone.
        new_role = role if role is not None and role != user.role else None
        if new_name:
            changes.append(f"name '{user.name}' to '{new_name}'")
        if new_role:
            changes.append(f"role {user.role} to {new_role}")
        if changes:
            plan.append(
                _Planned(
                    line,
                    "update",
                    "Changes " + " and ".join(changes) + ".",
                    existing=user,
                    new_name=new_name,
                    new_role=new_role,
                )
            )
        else:
            plan.append(_Planned(line, "unchanged", existing=user))
    return plan


def _missing(db: Session, plan: list[_Planned], actor: User) -> list[UserImportMissing]:
    in_file = {p.line.email for p in plan}
    return [
        UserImportMissing(id=u.id, name=u.name, email=u.email, role=u.role)
        for u in user_repository.list_all(db)
        if u.is_active and u.id != actor.id and u.email.lower() not in in_file
    ]


def _row(planned: _Planned) -> UserImportRow:
    role = planned.new_role or (planned.existing.role if planned.existing else planned.line.role)
    return UserImportRow(
        line=planned.line.number,
        name=planned.line.name,
        email=planned.line.email,
        role=str(role) if role else None,
        action=planned.action,
        note=planned.note,
    )


def preview(db: Session, content: bytes, actor: User) -> UserImportPreview:
    plan = _plan(db, content, actor)
    count = {
        a: sum(1 for p in plan if p.action == a) for a in ("create", "update", "unchanged", "skip")
    }
    return UserImportPreview(
        rows=[_row(p) for p in plan],
        missing_from_file=_missing(db, plan, actor),
        **count,
    )


def run(db: Session, content: bytes, actor: User) -> UserImportResult:
    plan = _plan(db, content, actor)
    created: list[UserImportCreated] = []
    skipped = [_row(p) for p in plan if p.action == "skip"]
    updated = 0

    for planned in plan:
        line = planned.line
        if planned.action == "create":
            role = planned.new_role or DEFAULT_ROLE
            password = user_service.temporary_password(line.email, line.name)
            try:
                user_service.create_user(
                    db,
                    UserCreate(name=line.name, email=line.email, password=password, role=role),
                    actor.id,
                )
            except (ConflictError, ValidationError) as error:
                skipped.append(_row(_Planned(line, "skip", str(error))))
                continue
            created.append(
                UserImportCreated(
                    name=line.name, email=line.email, role=str(role), temporary_password=password
                )
            )
        elif planned.action == "update" and planned.existing is not None:
            user = planned.existing
            changes: dict[str, str] = {}
            if planned.new_name:
                user.name = planned.new_name
                changes["name"] = planned.new_name
            if planned.new_role:
                user.role = planned.new_role
                changes["role"] = planned.new_role
            user_repository.save(db, user)
            audit_service.log(db, user_service.ENTITY_TYPE, user.id, "updated", actor.id, changes)
            if planned.new_role:
                # What their open sessions were allowed to do has changed.
                auth_service.end_sessions(db, user.id)
            updated += 1

    unchanged = sum(1 for p in plan if p.action == "unchanged")
    # The passwords are deliberately not part of this record.
    audit_service.log(
        db,
        user_service.ENTITY_TYPE,
        actor.id,
        "imported_users",
        actor.id,
        {
            "created": len(created),
            "updated": updated,
            "unchanged": unchanged,
            "skipped": len(skipped),
        },
    )
    return UserImportResult(
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped=sorted(skipped, key=lambda r: r.line),
        password_expires_on=auth_service.temporary_password_deadline().date(),
        missing_from_file=_missing(db, plan, actor),
    )
