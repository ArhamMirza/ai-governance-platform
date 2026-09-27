import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { correctiveActionsApi } from "./api";
import type { CorrectiveActionCreateInput, CorrectiveActionUpdateInput } from "./types";

export const correctiveActionsKey = ["corrective-actions"] as const;
export const correctiveActionKey = (id: number) => ["corrective-actions", id] as const;
export const correctiveActionAuditLogKey = (id: number) =>
  ["audit-log", "CorrectiveAction", id] as const;

export function useCorrectiveActions() {
  return useQuery({ queryKey: correctiveActionsKey, queryFn: correctiveActionsApi.list });
}

export function useCorrectiveAction(id: number) {
  return useQuery({
    queryKey: correctiveActionKey(id),
    queryFn: () => correctiveActionsApi.get(id),
  });
}

export function useCreateCorrectiveAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CorrectiveActionCreateInput) => correctiveActionsApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: correctiveActionsKey }),
  });
}

/** Every status-changing mutation moves the dashboard's overdue count and
 * "my corrective actions" list as well as the record itself. */
function invalidateCorrectiveAction(queryClient: QueryClient, id: number) {
  queryClient.invalidateQueries({ queryKey: correctiveActionsKey });
  queryClient.invalidateQueries({ queryKey: correctiveActionKey(id) });
  queryClient.invalidateQueries({ queryKey: correctiveActionAuditLogKey(id) });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useUpdateCorrectiveAction(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CorrectiveActionUpdateInput) => correctiveActionsApi.update(id, data),
    onSuccess: () => invalidateCorrectiveAction(queryClient, id),
  });
}

export function useDeleteCorrectiveAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => correctiveActionsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: correctiveActionsKey }),
  });
}

export function useSubmitForVerification(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => correctiveActionsApi.submitForVerification(id),
    onSuccess: () => invalidateCorrectiveAction(queryClient, id),
  });
}

export function useVerifyAndClose(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => correctiveActionsApi.verifyAndClose(id),
    onSuccess: () => invalidateCorrectiveAction(queryClient, id),
  });
}

export function useReopenCorrectiveAction(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => correctiveActionsApi.reopen(id),
    onSuccess: () => invalidateCorrectiveAction(queryClient, id),
  });
}
