import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { organizationContextApi } from "./api";
import type { OrganizationContextUpdateInput } from "./types";

const organizationContextKey = ["organization-context"] as const;
export const organizationIssuesKey = ["organization-context", "issues"] as const;
export const interestedPartiesKey = ["organization-context", "interested-parties"] as const;
const organizationContextAuditLogKey = ["audit-log", "OrganizationContext"] as const;

export function useOrganizationContext() {
  return useQuery({ queryKey: organizationContextKey, queryFn: organizationContextApi.get });
}

function invalidateAll(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: organizationContextKey });
  queryClient.invalidateQueries({ queryKey: organizationIssuesKey });
  queryClient.invalidateQueries({ queryKey: interestedPartiesKey });
  queryClient.invalidateQueries({ queryKey: organizationContextAuditLogKey });
}

export function useUpdateOrganizationContext() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: OrganizationContextUpdateInput) => organizationContextApi.update(data),
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useSubmitOrganizationContextForReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => organizationContextApi.submitForReview(),
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useApproveOrganizationContext() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => organizationContextApi.approve(),
    onSuccess: () => {
      invalidateAll(queryClient);
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
  });
}
