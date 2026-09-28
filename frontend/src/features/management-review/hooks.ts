import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { managementReviewApi } from "./api";
import type {
  ManagementReviewMeetingCreateInput,
  ManagementReviewMeetingUpdateInput,
  ManagementReviewSettingsUpdateInput,
} from "./types";

export const managementReviewSettingsKey = ["management-review", "settings"] as const;
export const managementReviewSettingsAuditLogKey = [
  "audit-log",
  "ManagementReviewSettings",
  1,
] as const;
export const managementReviewMeetingsKey = ["management-review", "meetings"] as const;
export const managementReviewMeetingKey = (id: number) =>
  ["management-review", "meetings", id] as const;
export const managementReviewMeetingAuditLogKey = (id: number) =>
  ["audit-log", "ManagementReviewMeeting", id] as const;

export function useManagementReviewSettings() {
  return useQuery({
    queryKey: managementReviewSettingsKey,
    queryFn: managementReviewApi.getSettings,
  });
}

function invalidateSettings(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: managementReviewSettingsKey });
  queryClient.invalidateQueries({ queryKey: managementReviewSettingsAuditLogKey });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useUpdateManagementReviewSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ManagementReviewSettingsUpdateInput) =>
      managementReviewApi.updateSettings(data),
    onSuccess: () => invalidateSettings(queryClient),
  });
}

export function useManagementReviewMeetings() {
  return useQuery({
    queryKey: managementReviewMeetingsKey,
    queryFn: managementReviewApi.listMeetings,
  });
}

export function useManagementReviewMeeting(id: number) {
  return useQuery({
    queryKey: managementReviewMeetingKey(id),
    queryFn: () => managementReviewApi.getMeeting(id),
  });
}

export function useCreateManagementReviewMeeting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ManagementReviewMeetingCreateInput) =>
      managementReviewApi.createMeeting(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: managementReviewMeetingsKey });
      invalidateSettings(queryClient);
    },
  });
}

function invalidateMeeting(queryClient: QueryClient, id: number) {
  queryClient.invalidateQueries({ queryKey: managementReviewMeetingsKey });
  queryClient.invalidateQueries({ queryKey: managementReviewMeetingKey(id) });
  queryClient.invalidateQueries({ queryKey: managementReviewMeetingAuditLogKey(id) });
  invalidateSettings(queryClient);
}

export function useUpdateManagementReviewMeeting(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ManagementReviewMeetingUpdateInput) =>
      managementReviewApi.updateMeeting(id, data),
    onSuccess: () => invalidateMeeting(queryClient, id),
  });
}

export function useDeleteManagementReviewMeeting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => managementReviewApi.removeMeeting(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: managementReviewMeetingsKey });
      invalidateSettings(queryClient);
    },
  });
}
