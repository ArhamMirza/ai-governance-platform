from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.routers import (
    ai_system_inventory,
    evidence,
    folders,
    health,
    policies,
    procedures,
    risk_assessments,
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


app.include_router(health.router, prefix="/api/v1")
app.include_router(policies.router, prefix="/api/v1")
app.include_router(procedures.router, prefix="/api/v1")
app.include_router(folders.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(ai_system_inventory.router, prefix="/api/v1")
app.include_router(risk_assessments.router, prefix="/api/v1")
