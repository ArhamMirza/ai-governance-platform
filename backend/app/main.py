from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.dependencies import get_current_user
from app.routers import (
    ai_system_inventory,
    audit_log,
    auth,
    dashboard,
    evidence,
    folders,
    framework_controls,
    framework_mapping,
    framework_soa,
    framework_tags,
    health,
    policies,
    procedures,
    risk_assessments,
    risk_criteria,
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


@app.exception_handler(AuthorizationError)
def authorization_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


# Every business router requires a logged-in session (reads included, not
# just writes) via this shared dependency. health and auth stay public --
# auth obviously so, since it's how you get a session in the first place.
_protected = [Depends(get_current_user)]

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1", dependencies=_protected)
app.include_router(procedures.router, prefix="/api/v1", dependencies=_protected)
app.include_router(folders.router, prefix="/api/v1", dependencies=_protected)
app.include_router(evidence.router, prefix="/api/v1", dependencies=_protected)
app.include_router(ai_system_inventory.router, prefix="/api/v1", dependencies=_protected)
app.include_router(risk_assessments.router, prefix="/api/v1", dependencies=_protected)
app.include_router(audit_log.router, prefix="/api/v1", dependencies=_protected)
app.include_router(dashboard.router, prefix="/api/v1", dependencies=_protected)
app.include_router(risk_criteria.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_controls.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_tags.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_mapping.router, prefix="/api/v1", dependencies=_protected)
app.include_router(framework_soa.router, prefix="/api/v1", dependencies=_protected)
app.include_router(users.router, prefix="/api/v1", dependencies=_protected)
