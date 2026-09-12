import { httpClient } from "../../shared/api/httpClient";
import type {
  CaigoDelegation,
  CaigoDelegationInput,
  GovernanceRole,
  GovernanceRoleCreateInput,
  GovernanceRoleUpdateInput,
  OrgChartNode,
} from "./types";

export const governanceRolesApi = {
  list: () => httpClient.get<GovernanceRole[]>("/governance-roles"),
  orgChart: () => httpClient.get<OrgChartNode[]>("/governance-roles/org-chart"),
  create: (data: GovernanceRoleCreateInput) =>
    httpClient.post<GovernanceRole>("/governance-roles", data),
  update: (roleId: number, data: GovernanceRoleUpdateInput) =>
    httpClient.patch<GovernanceRole>(`/governance-roles/${roleId}`, data),
  remove: (roleId: number) => httpClient.delete<void>(`/governance-roles/${roleId}`),
  assign: (roleId: number, userId: number) =>
    httpClient.post<GovernanceRole>(`/governance-roles/${roleId}/assignments`, {
      user_id: userId,
    }),
  unassign: (roleId: number, userId: number) =>
    httpClient.delete<GovernanceRole>(`/governance-roles/${roleId}/assignments/${userId}`),
  getCaigoDelegation: () =>
    httpClient.get<CaigoDelegation | null>("/governance-roles/caigo-delegation"),
  setCaigoDelegation: (data: CaigoDelegationInput) =>
    httpClient.post<CaigoDelegation>("/governance-roles/caigo-delegation", data),
  revokeCaigoDelegation: () =>
    httpClient.delete<void>("/governance-roles/caigo-delegation"),
};
