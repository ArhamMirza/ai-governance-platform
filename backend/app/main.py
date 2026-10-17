from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
    ValidationError,
)
from app.dependencies import get_current_user, get_internal_user
from app.routers import (
    agent,
    ai_assist,
    ai_incidents,
    ai_roles,
    ai_system_inventory,
    ai_system_lifecycle,
    ai_tools,
    ai_use,
    assistant,
    audit_log,
    auth,
    changes,
    communications,
    competence,
    compliance_status,
    concerns,
    corrective_actions,
    dashboard,
    data_inventory,
    dlp_rules,
    eu_ai_act,
    evidence,
    folders,
    framework_controls,
    framework_mapping,
    framework_soa,
    framework_tags,
    governance_roles,
    health,
    impact_assessment_drafts,
    impact_assessments,
    improvements,
    internal_audits,
    management_review,
    objectives,
    organization_context,
    organization_context_drafts,
    policies,
    policy_drafts,
    procedure_drafts,
    procedures,
    risk_assessments,
    risk_criteria,
    risk_item_suggestions,
    staff_portal,
    suppliers,
    users,
)

settings = get_settings()

app = FastAPI(title="AI Governance Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # So a client reading the agent policy from a page (not only from the extension)
    # can see its ETag and ask "has it changed?" with If-None-Match.
    expose_headers=["ETag"],
)


@app.exception_handler(NotFoundError)
def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
def authentication_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(ServiceUnavailableError)
def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AuthorizationError)
def authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(RateLimitedError)
def rate_limited_handler(request: Request, exc: RateLimitedError) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": str(exc)})


# Every business router requires a logged-in session (reads included, not
# just writes) via this shared dependency, and refuses an employee login:
# employees reach only the staff portal below. health and auth stay public
# -- auth obviously so, since it's how you get a session in the first place.
_protected = [Depends(get_internal_user)]

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(
    staff_portal.router, prefix="/api/v1", dependencies=[Depends(get_current_user)]
)
app.include_router(policies.router, prefix="/api/v1", dependencies=_protected)
app.include_router(policy_drafts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(procedures.router, prefix="/api/v1", dependencies=_protected)
app.include_router(procedure_drafts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(organization_context.router, prefix="/api/v1", dependencies=_protected)
app.include_router(organization_context_drafts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(folders.router, prefix="/api/v1", dependencies=_protected)
app.include_router(evidence.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_system_inventory.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_system_lifecycle.router, prefix="/api/v1", dependencies=_protected)
app.include_router(data_inventory.router, prefix="/api/v1", dependencies=_protected)
app.include_router(risk_assessments.router, prefix="/api/v1", dependencies=_protected)
app.include_router(
    impact_assessments.risk_assessments_router, prefix="/api/v1", dependencies=_protected
)
app.include_router(impact_assessments.router, prefix="/api/v1", dependencies=_protected)
app.include_router(audit_log.router, prefix="/api/v1", dependencies=_protected)
app.include_router(dashboard.router, prefix="/api/v1", dependencies=_protected)
app.include_router(risk_criteria.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_controls.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_tags.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_mapping.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_soa.router, prefix="/api/v1", dependencies=_protected)
app.include_router(compliance_status.router, prefix="/api/v1", dependencies=_protected)
app.include_router(users.router, prefix="/api/v1", dependencies=_protected)
app.include_router(governance_roles.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_assist.router, prefix="/api/v1", dependencies=_protected)
app.include_router(assistant.router, prefix="/api/v1", dependencies=_protected)
app.include_router(impact_assessment_drafts.router, prefix="/api/v1", dependencies=_protected)
app.include_router(risk_item_suggestions.router, prefix="/api/v1", dependencies=_protected)
app.include_router(corrective_actions.router, prefix="/api/v1", dependencies=_protected)
app.include_router(internal_audits.router, prefix="/api/v1", dependencies=_protected)
app.include_router(management_review.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_incidents.router, prefix="/api/v1", dependencies=_protected)
app.include_router(competence.router, prefix="/api/v1", dependencies=_protected)
app.include_router(suppliers.router, prefix="/api/v1", dependencies=_protected)
app.include_router(eu_ai_act.router, prefix="/api/v1", dependencies=_protected)
app.include_router(objectives.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_roles.router, prefix="/api/v1", dependencies=_protected)
app.include_router(changes.router, prefix="/api/v1", dependencies=_protected)
app.include_router(concerns.router, prefix="/api/v1", dependencies=_protected)
app.include_router(improvements.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_tools.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_use.router, prefix="/api/v1", dependencies=_protected)
app.include_router(dlp_rules.router, prefix="/api/v1", dependencies=_protected)
# The browser extension has no session: its routes take the enrollment key instead
# (dependencies.require_agent_key), not the signed-in-user rule above.
app.include_router(agent.router, prefix="/api/v1")
app.include_router(communications.router, prefix="/api/v1", dependencies=_protected)
