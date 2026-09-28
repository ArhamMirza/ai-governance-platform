from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_actor_id
from app.models.competence_requirement import CompetenceRequirement
from app.schemas.competence import (
    CompetenceRecordCreate,
    CompetenceRecordRead,
    CompetenceRequirementCreate,
    CompetenceRequirementRead,
    CompetenceRequirementSummary,
    CompetenceRequirementUpdate,
    PersonCompetence,
)
from app.services import competence_service, framework_service

router = APIRouter(prefix="/competence", tags=["competence"])


def _summary(
    requirement: CompetenceRequirement, people: list[PersonCompetence]
) -> CompetenceRequirementSummary:
    gaps = competence_service.gap_count(people)
    return CompetenceRequirementSummary(
        id=requirement.id,
        title=requirement.title,
        description=requirement.description,
        governance_role_id=requirement.governance_role_id,
        refresh_interval_months=requirement.refresh_interval_months,
        required_count=len(people),
        current_count=len(people) - gaps,
        gap_count=gaps,
        created_at=requirement.created_at,
        updated_at=requirement.updated_at,
    )


def _to_read(db: Session, requirement: CompetenceRequirement) -> CompetenceRequirementRead:
    people = competence_service.people_for(db, requirement)
    return CompetenceRequirementRead(
        **_summary(requirement, people).model_dump(),
        people=people,
        records=[
            CompetenceRecordRead.model_validate(record)
            for record in competence_service.list_records(db, requirement.id)
        ],
        framework_tags=framework_service.get_tags(
            db, competence_service.REQUIREMENT_ENTITY_TYPE, requirement.id
        ),
    )


@router.get("/requirements", response_model=list[CompetenceRequirementSummary])
def list_requirements(db: Session = Depends(get_db)) -> list[CompetenceRequirementSummary]:
    return [
        _summary(requirement, people) for requirement, people in competence_service.standings(db)
    ]


@router.post("/requirements", response_model=CompetenceRequirementRead, status_code=201)
def create_requirement(
    data: CompetenceRequirementCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CompetenceRequirementRead:
    return _to_read(db, competence_service.create_requirement(db, data, actor_id))


@router.get("/requirements/{requirement_id}", response_model=CompetenceRequirementRead)
def get_requirement(
    requirement_id: int, db: Session = Depends(get_db)
) -> CompetenceRequirementRead:
    return _to_read(db, competence_service.get_requirement(db, requirement_id))


@router.put("/requirements/{requirement_id}", response_model=CompetenceRequirementRead)
def update_requirement(
    requirement_id: int,
    data: CompetenceRequirementUpdate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CompetenceRequirementRead:
    return _to_read(db, competence_service.update_requirement(db, requirement_id, data, actor_id))


@router.delete("/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    requirement_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    competence_service.delete_requirement(db, requirement_id, actor_id)


@router.post(
    "/requirements/{requirement_id}/records",
    response_model=CompetenceRecordRead,
    status_code=201,
)
def record_completion(
    requirement_id: int,
    data: CompetenceRecordCreate,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> CompetenceRecordRead:
    record = competence_service.record_completion(db, requirement_id, data, actor_id)
    return CompetenceRecordRead.model_validate(record)


@router.delete("/records/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    actor_id: int | None = Depends(get_current_actor_id),
) -> None:
    competence_service.delete_record(db, record_id, actor_id)
