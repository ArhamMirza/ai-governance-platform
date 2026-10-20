from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_manage_users_user
from app.models.user import User
from app.schemas.auth import UserRead
from app.schemas.user import (
    TemporaryPassword,
    UserAccountabilities,
    UserCreate,
    UserDirectoryEntry,
    UserUpdate,
)
from app.schemas.user_import import UserImportPreview, UserImportResult
from app.services import governance_role_service, mfa_service, user_import_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead], dependencies=[Depends(require_manage_users_user)])
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    return user_service.list_users(db)


@router.get(
    "/directory",
    response_model=list[UserDirectoryEntry],
    dependencies=[Depends(get_current_user)],
)
def list_directory(db: Session = Depends(get_db)) -> list[UserDirectoryEntry]:
    """Any logged-in user can see id+name of everyone -- used to populate
    pickers like risk item ownership. Deliberately excludes email/role/
    active-status, which GET /users (admin-only) still guards."""
    roles_by_user = governance_role_service.role_names_by_user(db)
    return [
        UserDirectoryEntry(
            id=user.id, name=user.name, governance_roles=roles_by_user.get(user.id, [])
        )
        for user in user_service.list_users(db)
    ]


@router.get(
    "/{user_id}/accountabilities",
    response_model=UserAccountabilities,
    dependencies=[Depends(require_manage_users_user)],
)
def get_accountabilities(user_id: int, db: Session = Depends(get_db)) -> UserAccountabilities:
    """What this user is on the hook for -- read before deactivating them, so
    an admin knows what needs reassigning rather than finding out from a
    stuck approval later."""
    return user_service.get_accountabilities(db, user_id)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserRead:
    return user_service.create_user(db, data, actor.id)


@router.post("/import/preview", response_model=UserImportPreview)
def preview_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserImportPreview:
    """What a CSV of staff would do, without doing any of it."""
    return user_import_service.preview(db, file.file.read(user_import_service.MAX_BYTES + 1), actor)


@router.post("/import", response_model=UserImportResult)
def run_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserImportResult:
    """Creates and updates the accounts in a CSV. The starting passwords of the
    new ones are in this response and nowhere else."""
    return user_import_service.run(db, file.file.read(user_import_service.MAX_BYTES + 1), actor)


@router.post("/{user_id}/reset-password", response_model=TemporaryPassword)
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> TemporaryPassword:
    """Sets a one-time password, shown here once, and signs the person out
    everywhere. They must choose their own at their next sign-in."""
    return TemporaryPassword(temporary_password=user_service.reset_password(db, user_id, actor.id))


@router.post("/{user_id}/reset-two-step", response_model=UserRead)
def reset_two_step(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserRead:
    """For someone who has lost their phone and their recovery codes. Signs
    them out everywhere; if the organization requires two-step sign-in they
    must set it up again before doing anything else."""
    return mfa_service.admin_reset(db, user_id, actor.id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserRead:
    return user_service.update_user(db, user_id, data, actor.id)
