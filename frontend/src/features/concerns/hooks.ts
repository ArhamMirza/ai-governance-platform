import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { concernsApi, staffConcernsApi } from "./api";
import type {
  ConcernLogInput,
  ConcernSettingsInput,
  ConcernStatusInput,
  ConcernSubmitInput,
  ConcernUpdateInput,
  RaiseCorrectiveActionInput,
} from "./types";

// ---------- an employee's ----------

export const myConcernsKey = ["staff", "concerns", "mine"] as const;

export function useConcernsProcess() {
  return useQuery({ queryKey: ["staff", "concerns-process"], queryFn: staffConcernsApi.process });
}

export function useStaffAISystems() {
  return useQuery({ queryKey: ["staff", "ai-systems"], queryFn: staffConcernsApi.aiSystems });
}

export function useMyConcerns() {
  return useQuery({ queryKey: myConcernsKey, queryFn: staffConcernsApi.mine });
}

export function useSubmitConcern() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConcernSubmitInput) => staffConcernsApi.submit(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: myConcernsKey }),
  });
}

/** Not a query: a lookup spends one of a few guesses when it misses, so it
 * runs when the person asks and is never retried or refetched. */
export function useLookupConcern() {
  return useMutation({
    mutationFn: (trackingCode: string) => staffConcernsApi.lookup(trackingCode),
    retry: false,
  });
}

// ---------- a handler's ----------

export const concernsKey = ["concerns"] as const;
export const concernKey = (id: number) => ["concerns", id] as const;

export function useConcernAccess() {
  return useQuery({
    queryKey: ["concerns", "access"],
    queryFn: concernsApi.access,
    staleTime: 5 * 60 * 1000,
  });
}

export function useConcerns() {
  return useQuery({ queryKey: concernsKey, queryFn: concernsApi.list });
}

export function useConcern(id: number) {
  return useQuery({ queryKey: concernKey(id), queryFn: () => concernsApi.get(id) });
}

export function useConcernCorrectiveActions(id: number) {
  return useQuery({
    queryKey: ["concerns", id, "corrective-actions"],
    queryFn: () => concernsApi.listCorrectiveActions(id),
  });
}

export function useConcernSettings() {
  return useQuery({ queryKey: ["concerns", "settings"], queryFn: concernsApi.settings });
}

/** Any change can move a concern's standing, which shows on the register, the
 * dashboard and the compliance view -- and lands in its audit log. */
function invalidateConcerns(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: concernsKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "Concern"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
  // What the reporter sees moves with it.
  queryClient.invalidateQueries({ queryKey: myConcernsKey });
}

export function useLogConcern() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConcernLogInput) => concernsApi.log(data),
    onSuccess: () => invalidateConcerns(queryClient),
  });
}

export function useUpdateConcern(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConcernUpdateInput) => concernsApi.update(id, data),
    onSuccess: () => invalidateConcerns(queryClient),
  });
}

export function useSetConcernStatus(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConcernStatusInput) => concernsApi.setStatus(id, data),
    onSuccess: () => invalidateConcerns(queryClient),
  });
}

export function useRaiseIncidentFromConcern(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => concernsApi.raiseIncident(id),
    onSuccess: () => {
      invalidateConcerns(queryClient);
      queryClient.invalidateQueries({ queryKey: ["ai-incidents"] });
    },
  });
}

export function useRaiseCorrectiveActionFromConcern(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RaiseCorrectiveActionInput) => concernsApi.raiseCorrectiveAction(id, data),
    onSuccess: () => {
      invalidateConcerns(queryClient);
      queryClient.invalidateQueries({ queryKey: ["concerns", id, "corrective-actions"] });
      queryClient.invalidateQueries({ queryKey: ["corrective-actions"] });
    },
  });
}

export function useUpdateConcernSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConcernSettingsInput) => concernsApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["concerns", "settings"] });
      queryClient.invalidateQueries({ queryKey: ["staff", "concerns-process"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      invalidateConcerns(queryClient);
    },
  });
}
