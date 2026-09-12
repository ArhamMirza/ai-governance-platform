export interface RoleHolder {
  id: number;
  name: string;
}

export interface GovernanceRole {
  id: number;
  name: string;
  responsibilities: string;
  max_holders: number | null;
  parent_role_id: number | null;
  holders: RoleHolder[];
  created_at: string;
  updated_at: string;
}

export interface OrgChartNode {
  id: number;
  name: string;
  parent_role_id: number | null;
  max_holders: number | null;
  holders: RoleHolder[];
}

export interface GovernanceRoleCreateInput {
  name: string;
  responsibilities: string;
  parent_role_id?: number | null;
  max_holders?: number | null;
}

export interface GovernanceRoleUpdateInput {
  name?: string;
  responsibilities?: string;
  parent_role_id?: number | null;
  max_holders?: number | null;
}

export interface CaigoDelegation {
  id: number;
  delegate_user_id: number;
  delegate_name: string;
  starts_at: string;
  ends_at: string;
}

export interface CaigoDelegationInput {
  delegate_user_id: number;
  ends_at: string;
}
