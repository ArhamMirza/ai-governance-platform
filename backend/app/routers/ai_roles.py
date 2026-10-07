from fastapi import APIRouter

from app.core import ai_stakeholder_roles
from app.schemas.ai_roles import AIRoleRead

router = APIRouter(prefix="/ai-roles", tags=["ai-roles"])


@router.get("", response_model=list[AIRoleRead])
def list_ai_roles() -> list[AIRoleRead]:
    """The ISO/IEC 22989 AI roles an organization can hold, grouped by their
    main role -- so the frontend doesn't keep its own copy of the list."""
    return [
        AIRoleRead(
            code=role.code, label=role.label, parent=role.parent, description=role.description
        )
        for role in ai_stakeholder_roles.AI_ROLES
    ]
