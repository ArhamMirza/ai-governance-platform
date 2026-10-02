from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.supplier_schedule import ContractStatus
from app.models.supplier import SupplierStatus, SupplierType
from app.models.supplier_ai_system import SupplierRole
from app.models.supplier_review import SupplierReviewOutcome
from app.schemas.framework_control import FrameworkControlRead


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    supplier_type: SupplierType = SupplierType.OTHER
    description: str | None = None
    owner_id: int | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contract_reference: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None
    review_interval_months: int | None = Field(default=None, ge=1)
    first_review_due: date | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    supplier_type: SupplierType | None = None
    description: str | None = None
    status: SupplierStatus | None = None
    owner_id: int | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contract_reference: str | None = None
    contract_start: date | None = None
    contract_end: date | None = None
    responsibilities: str | None = None
    requirements: str | None = None
    review_interval_months: int | None = Field(default=None, ge=1)
    first_review_due: date | None = None


class SupplierAISystemsUpdate(BaseModel):
    ai_system_row_ids: list[int]


class SupplierAISystemLinkUpdate(BaseModel):
    supplier_role: SupplierRole | None = None
    rebranded: bool = False
    substantially_modified: bool = False
    repurposed_to_high_risk: bool = False


class SupplierAISystemLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ai_system_row_id: int
    supplier_role: SupplierRole | None
    rebranded: bool
    substantially_modified: bool
    repurposed_to_high_risk: bool
    # Computed from the three above -- the organization may be this
    # system's provider under EU AI Act Art. 25(1).
    art25_triggered: bool


class SupplierRiskItemRead(BaseModel):
    """A risk item whose Supplier cell names this supplier."""

    risk_assessment_id: int
    row_id: int
    ai_system_row_id: int
    category: str | None
    description: str | None
    status: str | None


class SupplierReviewCreate(BaseModel):
    review_date: date
    outcome: SupplierReviewOutcome = SupplierReviewOutcome.SATISFACTORY
    notes: str | None = None


class SupplierReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    review_date: date
    outcome: SupplierReviewOutcome
    notes: str | None
    reviewed_by: int | None
    created_at: datetime


class SupplierRead(BaseModel):
    id: int
    name: str
    supplier_type: SupplierType
    description: str | None
    status: SupplierStatus
    owner_id: int | None
    contact_name: str | None
    contact_email: str | None
    contract_reference: str | None
    contract_start: date | None
    contract_end: date | None
    responsibilities: str | None
    requirements: str | None
    review_interval_months: int | None
    first_review_due: date | None
    ai_system_row_ids: list[int]
    ai_system_links: list[SupplierAISystemLinkRead]
    next_review_due: date | None
    review_overdue: bool
    contract_status: ContractStatus | None
    framework_tags: list[FrameworkControlRead]
    created_at: datetime
    updated_at: datetime


class SupplierDetailRead(SupplierRead):
    reviews: list[SupplierReviewRead]
