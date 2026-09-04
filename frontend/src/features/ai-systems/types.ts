export interface GateRequirement {
  key: string;
  label: string;
  satisfied: boolean;
  detail: string;
}

export interface AISystemLifecycle {
  ai_system_row_id: number;
  current_stage: string;
  current_stage_label: string;
  next_stage: string | null;
  next_stage_label: string | null;
  entered_stage_at: string;

  deployment_environment: string | null;
  deployment_version: string | null;
  deployed_at: string | null;
  deployment_approved_by: number | null;
  deployment_approved_at: string | null;

  monitoring_owner_id: number | null;
  incident_escalation_path: string | null;

  retirement_reason: string | null;
  retirement_approved_by: number | null;
  retirement_approved_at: string | null;
  retired_at: string | null;
  retention_until: string | null;
  archived_at: string | null;
  is_archived: boolean;
  retention_expired: boolean;

  requirements: GateRequirement[];
  can_advance: boolean;
  can_archive: boolean;
}

export interface DeploymentRecordInput {
  deployment_environment?: string | null;
  deployment_version?: string | null;
  deployed_at?: string | null;
}

export interface MonitoringInput {
  monitoring_owner_id?: number | null;
  incident_escalation_path?: string | null;
}

export interface RetirementInput {
  retirement_reason?: string | null;
  retention_until?: string | null;
}

export interface ArchivedAISystem {
  ai_system_row_id: number;
  name: string;
  retirement_reason: string | null;
  retired_at: string | null;
  retention_until: string | null;
  archived_at: string | null;
  retention_expired: boolean;
}
