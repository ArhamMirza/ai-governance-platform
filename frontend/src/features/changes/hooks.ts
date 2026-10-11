import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { changesApi } from "./api";
import type { ChangeInput, ChangeStatusInput, ChangeUpdateInput } from "./types";

export const changesKey = ["changes"] as const;
export const changeKey = (id: number) => ["changes", id] as const;

export function useChanges() {
  return useQuery({ queryKey: changesKey, queryFn: () => changesApi.list() });
}

export function useChangesForAISystem(rowId: number) {
  return useQuery({
    queryKey: ["changes", "for-ai-system", rowId],
    queryFn: () => changesApi.list(rowId),
  });
}

export function useChangesAsOf(asOf: string) {
  return useQuery({
    queryKey: ["changes", "as-of", asOf],
    queryFn: () => changesApi.standingAsOf(asOf),
  });
}

export function useChange(id: number) {
  return useQuery({ queryKey: changeKey(id), queryFn: () => changesApi.get(id) });
}

/** Any change can move a change's standing, which shows on the list, its AI
 * systems' pages, management review, the dashboard and the compliance view
 * -- and lands in its audit log. */
function invalidateChanges(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: changesKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "ManagementSystemChange"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateChange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ChangeInput) => changesApi.create(data),
    onSuccess: () => invalidateChanges(queryClient),
  });
}

export function useUpdateChange(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ChangeUpdateInput) => changesApi.update(id, data),
    onSuccess: () => invalidateChanges(queryClient),
  });
}

export function useDeleteChange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => changesApi.remove(id),
    onSuccess: () => invalidateChanges(queryClient),
  });
}

export function useSetChangeStatus(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ChangeStatusInput) => changesApi.setStatus(id, data),
    onSuccess: () => invalidateChanges(queryClient),
  });
}

export function useSetChangeAISystems(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (aiSystemRowIds: number[]) => changesApi.setAISystems(id, aiSystemRowIds),
    onSuccess: () => invalidateChanges(queryClient),
  });
}
