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

  requirements: GateRequirement[];
  can_advance: boolean;
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
