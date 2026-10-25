from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, GettingStarted
from app.services import dashboard_service, getting_started_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> DashboardSummary:
    return dashboard_service.get_summary(db, user.id)


@router.get("/getting-started", response_model=GettingStarted)
def get_getting_started(
    db: Session = Depends(get_db), _user: User = Depends(get_current_user)
) -> GettingStarted:
    """What a new installation still needs, in the order to do it."""
    return getting_started_service.get(db)
