import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type AiAssistSettingsUpdate, type DraftRequest, aiAssistApi } from "./api";

export const aiStatusKey = ["ai-assist-status"];
export const aiSettingsKey = ["ai-assist-settings"];

/** Whether to offer AI at all. Every AI surface hides itself when this says
 * the deployment has no provider configured, so nobody is shown a button
 * that can only fail. */
export function useAiAssistStatus() {
  return useQuery({
    queryKey: aiStatusKey,
    queryFn: aiAssistApi.status,
    // Configuration changes rarely, and this gates UI on many pages.
    staleTime: 5 * 60 * 1000,
  });
}

export function useAiSettings() {
  return useQuery({ queryKey: aiSettingsKey, queryFn: aiAssistApi.getSettings });
}

export function useUpdateAiSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AiAssistSettingsUpdate) => aiAssistApi.updateSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aiSettingsKey });
      // Turning a provider on or off changes whether every AI button shows.
      queryClient.invalidateQueries({ queryKey: aiStatusKey });
    },
  });
}

/** Drafting is deliberately not a React Query mutation with cached state:
 * the result belongs to the field that asked for it, not to any server
 * cache, because nothing was saved. */
export function useDraftField() {
  return useMutation({ mutationFn: (data: DraftRequest) => aiAssistApi.draft(data) });
}
