"""The AI system life cycle stages, in ISO/IEC 5338 order.

Verification and validation deliberately precedes deployment: a system is
validated, then released. Stages are fixed -- the gate between each one (see
lifecycle_gate_service) is what makes them mean something, so an open-ended
set of stages would have nothing to enforce.
"""

from enum import StrEnum


class LifecycleStage(StrEnum):
    INCEPTION = "inception"
    DESIGN = "design"
    DEVELOPMENT = "development"
    VERIFICATION_AND_VALIDATION = "verification_and_validation"
    DEPLOYMENT = "deployment"
    OPERATION_AND_MONITORING = "operation_and_monitoring"
    RETIREMENT = "retirement"


STAGE_ORDER: list[LifecycleStage] = [
    LifecycleStage.INCEPTION,
    LifecycleStage.DESIGN,
    LifecycleStage.DEVELOPMENT,
    LifecycleStage.VERIFICATION_AND_VALIDATION,
    LifecycleStage.DEPLOYMENT,
    LifecycleStage.OPERATION_AND_MONITORING,
    LifecycleStage.RETIREMENT,
]

STAGE_LABELS: dict[LifecycleStage, str] = {
    LifecycleStage.INCEPTION: "Inception",
    LifecycleStage.DESIGN: "Design",
    LifecycleStage.DEVELOPMENT: "Development",
    LifecycleStage.VERIFICATION_AND_VALIDATION: "Verification & Validation",
    LifecycleStage.DEPLOYMENT: "Deployment",
    LifecycleStage.OPERATION_AND_MONITORING: "Operation & Monitoring",
    LifecycleStage.RETIREMENT: "Retirement",
}


def label(stage: str) -> str:
    try:
        return STAGE_LABELS[LifecycleStage(stage)]
    except ValueError:
        return stage


def next_stage(stage: str) -> LifecycleStage | None:
    """The stage after this one, or None at the end of the life cycle."""
    index = STAGE_ORDER.index(LifecycleStage(stage))
    if index + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[index + 1]


def previous_stage(stage: str) -> LifecycleStage | None:
    index = STAGE_ORDER.index(LifecycleStage(stage))
    if index == 0:
        return None
    return STAGE_ORDER[index - 1]
