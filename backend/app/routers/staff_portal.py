"""The employee home -- the only routes an employee login can reach, beyond
signing in and out. Mounted with plain get_current_user in app.main, unlike
every other router (which refuses employees)."""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.ai_tool import AIToolRequest
from app.models.concern import Concern
from app.models.user import User
from app.schemas.ai_tool import (
    AIToolRequestCreate,
    StaffAITool,
    StaffAIToolRequestRead,
    StaffRequestableTool,
)
from app.schemas.ai_use import StaffAIUseNotice
from app.schemas.concern import (
    ConcernLookup,
    ConcernsProcess,
    ConcernSubmit,
    ConcernSubmitted,
    ReporterConcernRead,
    StaffAISystem,
)
from app.schemas.staff import StaffLibraryItem
from app.services import ai_tool_service, ai_usage_service, concern_service, staff_service

router = APIRouter(prefix="/staff", tags=["staff"])


@router.get("/library", response_model=list[StaffLibraryItem])
def library(db: Session = Depends(get_db)) -> list[StaffLibraryItem]:
    return staff_service.library(db)


@router.get("/library/documents/{evidence_id}")
def download_document(evidence_id: int, db: Session = Depends(get_db)) -> FileResponse:
    evidence = staff_service.shared_document(db, evidence_id)
    return FileResponse(
        path=evidence.storage_path,
        filename=evidence.filename,
        media_type=evidence.content_type,
    )


def _reporter_view(concern: Concern) -> ReporterConcernRead:
    """What the person who raised it may see -- built field by field, so an
    internal field added to Concern later can't leak through."""
    return ReporterConcernRead(
        id=concern.id,
        category=concern.category,
        description=concern.description,
        received_on=concern.received_on,
        status=concern.status,
        acknowledged_on=concern.acknowledged_on,
        closed_on=concern.closed_on,
        outcome=concern.outcome,
        reply_to_reporter=concern.reply_to_reporter,
        is_anonymous=concern.is_anonymous,
    )


@router.get("/ai-systems", response_model=list[StaffAISystem])
def ai_systems(db: Session = Depends(get_db)) -> list[StaffAISystem]:
    """Which AI system a concern is about -- name and id, nothing else."""
    return [
        StaffAISystem(id=row_id, name=name)
        for row_id, name in concern_service.in_service_ai_systems(db)
    ]


@router.get("/concerns-process", response_model=ConcernsProcess)
def concerns_process(db: Session = Depends(get_db)) -> ConcernsProcess:
    settings = concern_service.settings_or_default(db)
    return ConcernsProcess(
        process_description=settings.process_description,
        acknowledge_within_days=settings.acknowledge_within_days,
    )


@router.post("/concerns", response_model=ConcernSubmitted, status_code=201)
def submit_concern(
    data: ConcernSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ConcernSubmitted:
    concern, code = concern_service.submit(db, user, data)
    return ConcernSubmitted(tracking_code=code, concern=_reporter_view(concern))


@router.get("/concerns/mine", response_model=list[ReporterConcernRead])
def my_concerns(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ReporterConcernRead]:
    return [_reporter_view(concern) for concern in concern_service.list_mine(db, user)]


# A POST, not a GET: the tracking code is a secret, and a URL ends up in
# server logs, browser history and referrers.
@router.post("/concerns/lookup", response_model=ReporterConcernRead)
def lookup_concern(
    data: ConcernLookup,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ReporterConcernRead:
    return _reporter_view(concern_service.lookup(db, user, data.tracking_code))


# ---------- AI tools ----------


def _own_request_view(request: AIToolRequest) -> StaffAIToolRequestRead:
    """An employee's own request and how it was answered -- built field by
    field, so an internal field can't leak through."""
    return StaffAIToolRequestRead(
        id=request.id,
        tool_name=request.tool_name,
        domain=request.domain,
        purpose=request.purpose,
        requested_on=request.requested_on,
        status=request.status,
        decided_on=request.decided_on,
        decision_note=request.decision_note,
    )


@router.get("/ai-tools", response_model=list[StaffAITool])
def approved_ai_tools(db: Session = Depends(get_db)) -> list[StaffAITool]:
    """The AI tools staff may use, with the rules that go with each."""
    return [
        StaffAITool(
            id=tool.id,
            name=tool.name,
            vendor=tool.vendor,
            domains=tool.domains,
            status=tool.status,
            max_data_classification=tool.max_data_classification,
            conditions_of_use=tool.conditions_of_use,
        )
        for tool in ai_tool_service.approved_tools(db)
    ]


@router.get("/ai-tools/requestable", response_model=list[StaffRequestableTool])
def requestable_ai_tools(db: Session = Depends(get_db)) -> list[StaffRequestableTool]:
    """Known tools that are not allowed yet, to pick from when asking."""
    return [
        StaffRequestableTool(id=tool.id, name=tool.name, vendor=tool.vendor)
        for tool in ai_tool_service.requestable_tools(db)
    ]


@router.post("/ai-tool-requests", response_model=StaffAIToolRequestRead, status_code=201)
def request_ai_tool(
    data: AIToolRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StaffAIToolRequestRead:
    return _own_request_view(ai_tool_service.create_request(db, data, user.id))


@router.get("/ai-tool-requests/mine", response_model=list[StaffAIToolRequestRead])
def my_ai_tool_requests(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[StaffAIToolRequestRead]:
    return [_own_request_view(r) for r in ai_tool_service.list_my_requests(db, user.id)]


@router.get("/ai-use-notice", response_model=StaffAIUseNotice)
def ai_use_notice(db: Session = Depends(get_db)) -> StaffAIUseNotice:
    """What staff are told about how their use of AI tools is monitored."""
    settings = ai_usage_service.settings_or_default(db)
    return StaffAIUseNotice(
        staff_notice=settings.staff_notice,
        unapproved_site_action=settings.unapproved_site_action,
    )
