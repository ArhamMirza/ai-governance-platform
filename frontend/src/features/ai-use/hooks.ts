import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { aiUseApi, dlpRulesApi, staffAiUseApi } from "./api";
import type { AIUseSettingsInput, DLPRuleInput, DLPRuleUpdateInput } from "./types";

export const dlpRulesKey = ["dlp-rules"] as const;
export const aiUseSettingsKey = ["ai-use", "settings"] as const;

export function useDLPRules() {
  return useQuery({ queryKey: dlpRulesKey, queryFn: () => dlpRulesApi.list() });
}

export function useBuiltinDetectors() {
  return useQuery({
    queryKey: ["dlp-rules", "detectors"],
    queryFn: () => dlpRulesApi.detectors(),
    // A fixed list, built into the server.
    staleTime: Infinity,
  });
}

/** A rule changes what the extension is told, the compliance view and the
 * rule's audit trail. */
function invalidateRules(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: dlpRulesKey });
  queryClient.invalidateQueries({ queryKey: ["audit-log", "DLPRule"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
}

export function useCreateDLPRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DLPRuleInput) => dlpRulesApi.create(data),
    onSuccess: () => invalidateRules(queryClient),
  });
}

export function useUpdateDLPRule(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DLPRuleUpdateInput) => dlpRulesApi.update(id, data),
    onSuccess: () => invalidateRules(queryClient),
  });
}

export function useDeleteDLPRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => dlpRulesApi.remove(id),
    onSuccess: () => invalidateRules(queryClient),
  });
}

export function useAIUseSettings() {
  return useQuery({ queryKey: aiUseSettingsKey, queryFn: () => aiUseApi.settings() });
}

export function useUpdateAIUseSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AIUseSettingsInput) => aiUseApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiUseSettingsKey });
      queryClient.invalidateQueries({ queryKey: ["staff-ai-use-notice"] });
      queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
      queryClient.invalidateQueries({ queryKey: ["ai-use", "usage"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log", "AIUseSettings"] });
    },
  });
}

export function useRotateEnrollmentKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => aiUseApi.rotateKey(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: aiUseSettingsKey }),
  });
}

export function useAIUsage(days: number) {
  return useQuery({
    queryKey: ["ai-use", "usage", days],
    queryFn: () => aiUseApi.usage(days),
  });
}

export function useStaffAIUseNotice() {
  return useQuery({ queryKey: ["staff-ai-use-notice"], queryFn: () => staffAiUseApi.notice() });
}
