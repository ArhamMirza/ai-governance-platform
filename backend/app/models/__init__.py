from app.models.ai_assist import AiAssistSettings, AiUsage
from app.models.ai_conversation import AiConversation, AiMessage, MessageRole
from app.models.ai_dlp import (
    AIUsageAction,
    AIUsageEvent,
    AIUsageEventType,
    AIUseSettings,
    DLPAction,
    DLPRule,
    DLPRuleKind,
)
from app.models.ai_draft import AiDraft, DraftStatus
from app.models.ai_incident import AIIncident, AIIncidentSeverity, AIIncidentStatus
from app.models.ai_objective import AIObjective, ObjectiveKind, ObjectiveStatus, TargetDirection
from app.models.ai_objective_ai_system import AIObjectiveAISystem
from app.models.ai_system_lifecycle import AISystemLifecycle
from app.models.ai_tool import (
    AITool,
    AIToolRequest,
    AIToolRequestStatus,
    AIToolStatus,
    DataClassification,
)
from app.models.audit_finding import AuditFinding, AuditFindingType
from app.models.audit_log import AuditLogEntry
from app.models.audit_program import AuditProgram, AuditProgramStatus, AuditScheduleType
from app.models.communication import (
    CommunicationDirection,
    CommunicationPlanItem,
    CommunicationRecord,
    CommunicationStatus,
)
from app.models.competence_record import CompetenceRecord
from app.models.competence_requirement import CompetenceRequirement
from app.models.concern import (
    Concern,
    ConcernCategory,
    ConcernChannel,
    ConcernOutcome,
    ConcernSettings,
    ConcernStatus,
)
from app.models.corrective_action import CorrectiveAction, CorrectiveActionStatus
from app.models.data_inventory_record import DataInventoryRecord
from app.models.document_chunk import ChunkSource, DocumentChunk, IndexStatus, SourceType
from app.models.eu_ai_act_applicability import EuAiActApplicability
from app.models.evidence import Evidence
from app.models.folder import Folder
from app.models.framework_control import FrameworkControl
from app.models.framework_soa_entry import FrameworkSoaEntry
from app.models.framework_tag import FrameworkTag
from app.models.governance_role import GovernanceRole
from app.models.governance_role_assignment import GovernanceRoleAssignment
from app.models.governance_role_delegation import GovernanceRoleDelegation
from app.models.impact_assessment import ImpactAssessment
from app.models.impact_factor_assessment import ImpactFactorAssessment
from app.models.improvement import Improvement, ImprovementSource, ImprovementStatus
from app.models.index_queue import IndexQueueEntry
from app.models.internal_audit import InternalAudit, InternalAuditStatus
from app.models.management_review_meeting import ManagementReviewMeeting
from app.models.management_review_settings import ManagementReviewSettings
from app.models.management_system_change import (
    ChangeAISystem,
    ChangeStatus,
    ChangeType,
    ManagementSystemChange,
)
from app.models.mfa import MFARecoveryCode, SecuritySettings, UserMFA
from app.models.objective_measurement import ObjectiveMeasurement
from app.models.organization_context import OrganizationContext, OrganizationContextStatus
from app.models.password_history import PasswordHistory
from app.models.policy import Policy
from app.models.procedure import Procedure
from app.models.risk_assessment import RiskAssessment
from app.models.risk_criteria import RiskCriteria
from app.models.session import Session
from app.models.sheet import Sheet, SheetRow
from app.models.supplier import Supplier, SupplierStatus, SupplierType
from app.models.supplier_ai_system import SupplierAISystem
from app.models.supplier_review import SupplierReview, SupplierReviewOutcome
from app.models.user import User

__all__ = [
    "AIIncident",
    "AIIncidentSeverity",
    "AIIncidentStatus",
    "AIObjective",
    "AIUsageAction",
    "AIUsageEvent",
    "AIUsageEventType",
    "AIUseSettings",
    "DLPAction",
    "DLPRule",
    "DLPRuleKind",
    "AITool",
    "AIToolRequest",
    "AIToolRequestStatus",
    "AIToolStatus",
    "DataClassification",
    "Concern",
    "ConcernCategory",
    "ConcernChannel",
    "ConcernOutcome",
    "ConcernSettings",
    "ConcernStatus",
    "CommunicationDirection",
    "CommunicationPlanItem",
    "CommunicationRecord",
    "CommunicationStatus",
    "ChangeAISystem",
    "ChangeStatus",
    "ChangeType",
    "ManagementSystemChange",
    "AIObjectiveAISystem",
    "AISystemLifecycle",
    "AiAssistSettings",
    "AiConversation",
    "AiDraft",
    "AiMessage",
    "AiUsage",
    "AuditFinding",
    "AuditFindingType",
    "AuditLogEntry",
    "AuditProgram",
    "AuditProgramStatus",
    "AuditScheduleType",
    "ChunkSource",
    "CompetenceRecord",
    "CompetenceRequirement",
    "CorrectiveAction",
    "CorrectiveActionStatus",
    "DataInventoryRecord",
    "DocumentChunk",
    "DraftStatus",
    "EuAiActApplicability",
    "Evidence",
    "Folder",
    "FrameworkControl",
    "FrameworkSoaEntry",
    "FrameworkTag",
    "GovernanceRole",
    "GovernanceRoleAssignment",
    "GovernanceRoleDelegation",
    "ImpactAssessment",
    "ImpactFactorAssessment",
    "Improvement",
    "ImprovementSource",
    "ImprovementStatus",
    "IndexQueueEntry",
    "IndexStatus",
    "InternalAudit",
    "InternalAuditStatus",
    "ManagementReviewMeeting",
    "ManagementReviewSettings",
    "MessageRole",
    "ObjectiveKind",
    "ObjectiveMeasurement",
    "ObjectiveStatus",
    "OrganizationContext",
    "OrganizationContextStatus",
    "Policy",
    "Procedure",
    "RiskAssessment",
    "RiskCriteria",
    "Session",
    "SourceType",
    "Sheet",
    "SheetRow",
    "Supplier",
    "SupplierAISystem",
    "SupplierReview",
    "SupplierReviewOutcome",
    "SupplierStatus",
    "SupplierType",
    "TargetDirection",
    "MFARecoveryCode",
    "PasswordHistory",
    "SecuritySettings",
    "UserMFA",
    "User",
]

# Imported last, once every model above exists: registering the listener
# that keeps the search index current needs all of them. Importing it here
# rather than from one entry point means the hook is attached anywhere the
# models are -- the app, a script, a test -- so nothing can write a record
# through a path that quietly skips reindexing.
from app.core import index_hooks  # noqa: E402,F401  (import for side effect)
