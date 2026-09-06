from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user, require_manage_users_user
from app.models.user import User
from app.schemas.auth import UserRead
from app.schemas.user import UserCreate, UserDirectoryEntry, UserUpdate
from app.services import governance_role_service, user_service

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


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserRead:
    return user_service.create_user(db, data, actor.id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_manage_users_user),
) -> UserRead:
    return user_service.update_user(db, user_id, data, actor.id)
