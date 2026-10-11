import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { communicationsApi } from "./api";
import type {
  CommunicationInput,
  CommunicationRecordInput,
  CommunicationUpdateInput,
} from "./types";

export const communicationsKey = ["communications"] as const;
export const communicationKey = (id: number) => ["communications", id] as const;

export function useCommunications() {
  return useQuery({ queryKey: communicationsKey, queryFn: communicationsApi.list });
}

export function useCommunication(id: number) {
  return useQuery({ queryKey: communicationKey(id), queryFn: () => communicationsApi.get(id) });
}

/** Any change can move the list's overdue flags, the dashboard's count and
 * the compliance view -- and lands in the item's audit log. */
function invalidateCommunications(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: communicationsKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "CommunicationPlanItem"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateCommunication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CommunicationInput) => communicationsApi.create(data),
    onSuccess: () => invalidateCommunications(queryClient),
  });
}

export function useUpdateCommunication(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CommunicationUpdateInput) => communicationsApi.update(id, data),
    onSuccess: () => invalidateCommunications(queryClient),
  });
}

export function useDeleteCommunication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => communicationsApi.remove(id),
    onSuccess: () => invalidateCommunications(queryClient),
  });
}

export function useRecordCommunication(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CommunicationRecordInput) => communicationsApi.record(id, data),
    onSuccess: () => invalidateCommunications(queryClient),
  });
}

export function useDeleteCommunicationRecord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (recordId: number) => communicationsApi.removeRecord(recordId),
    onSuccess: () => invalidateCommunications(queryClient),
  });
}
