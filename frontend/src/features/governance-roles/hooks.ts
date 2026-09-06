import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { governanceRolesApi } from "./api";
import type { GovernanceRoleCreateInput, GovernanceRoleUpdateInput } from "./types";

const rolesKey = ["governance-roles"] as const;
const orgChartKey = ["governance-roles", "org-chart"] as const;

function useInvalidateGovernanceRoles() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: rolesKey });
    queryClient.invalidateQueries({ queryKey: orgChartKey });
    // Every owner/assessor picker badges against this -- a role or
    // assignment change can change what any of them should show.
    queryClient.invalidateQueries({ queryKey: ["users", "directory"] });
  };
}

export function useGovernanceRoles() {
  return useQuery({ queryKey: rolesKey, queryFn: governanceRolesApi.list });
}

export function useOrgChart() {
  return useQuery({ queryKey: orgChartKey, queryFn: governanceRolesApi.orgChart });
}

export function useCreateGovernanceRole() {
  const invalidate = useInvalidateGovernanceRoles();
  return useMutation({
    mutationFn: (data: GovernanceRoleCreateInput) => governanceRolesApi.create(data),
    onSuccess: invalidate,
  });
}

export function useUpdateGovernanceRole() {
  const invalidate = useInvalidateGovernanceRoles();
  return useMutation({
    mutationFn: ({ roleId, data }: { roleId: number; data: GovernanceRoleUpdateInput }) =>
      governanceRolesApi.update(roleId, data),
    onSuccess: invalidate,
  });
}

export function useDeleteGovernanceRole() {
  const invalidate = useInvalidateGovernanceRoles();
  return useMutation({
    mutationFn: (roleId: number) => governanceRolesApi.remove(roleId),
    onSuccess: invalidate,
  });
}

export function useAssignGovernanceRole() {
  const invalidate = useInvalidateGovernanceRoles();
  return useMutation({
    mutationFn: ({ roleId, userId }: { roleId: number; userId: number }) =>
      governanceRolesApi.assign(roleId, userId),
    onSuccess: invalidate,
  });
}

export function useUnassignGovernanceRole() {
  const invalidate = useInvalidateGovernanceRoles();
  return useMutation({
    mutationFn: ({ roleId, userId }: { roleId: number; userId: number }) =>
      governanceRolesApi.unassign(roleId, userId),
    onSuccess: invalidate,
  });
}
