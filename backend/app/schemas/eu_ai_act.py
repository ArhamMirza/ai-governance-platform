from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.framework_soa_entry import SoaApplicability

EuAiActScope = Literal["not_assessed", "in_scope", "out_of_scope"]


class EuAiActApplicabilityUpdate(BaseModel):
    in_scope: bool | None
    scope_justification: str | None = None
    is_provider: bool = False
    is_deployer: bool = False
    is_importer: bool = False
    is_distributor: bool = False
    has_high_risk_systems: bool | None = None


class EuAiActApplicabilityRead(BaseModel):
    scope: EuAiActScope
    in_scope: bool | None
    scope_justification: str | None
    is_provider: bool
    is_deployer: bool
    is_importer: bool
    is_distributor: bool
    has_high_risk_systems: bool | None
    # A hint for the high-risk question, from the inventory's Risk Tier
    # column -- informative only, never used to decide applicability.
    high_risk_system_count: int
    updated_by: int | None
    updated_at: datetime | None


class EuAiActArticleOverrideUpdate(BaseModel):
    applicability: SoaApplicability
    justification: str


class EuAiActArticleRead(BaseModel):
    id: int
    code: str
    title: str
    automatic_applicable: bool
    automatic_reason: str
    override_applicability: SoaApplicability | None
    override_justification: str | None
    applicable: bool
    reason: str
