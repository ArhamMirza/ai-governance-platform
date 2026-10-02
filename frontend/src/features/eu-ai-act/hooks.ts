import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";

import { euAiActApi } from "./api";
import type { Applicability, EuAiActApplicabilityInput } from "./types";

const applicabilityKey = ["eu-ai-act", "applicability"] as const;
const articlesKey = ["eu-ai-act", "articles"] as const;

export function useEuAiActApplicability() {
  return useQuery({ queryKey: applicabilityKey, queryFn: euAiActApi.getApplicability });
}

export function useEuAiActArticles() {
  return useQuery({ queryKey: articlesKey, queryFn: euAiActApi.listArticles });
}

/** Applicability moves every EU AI Act figure: the article list, compliance
 * status and summary, and the dashboard's ring and alerts. */
function invalidateApplicability(queryClient: QueryClient) {
  queryClient.invalidateQueries({ queryKey: ["eu-ai-act"] });
  queryClient.invalidateQueries({ queryKey: ["compliance-status"] });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
}

export function useUpdateEuAiActApplicability() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: EuAiActApplicabilityInput) => euAiActApi.updateApplicability(data),
    onSuccess: () => invalidateApplicability(queryClient),
  });
}

export function useSetArticleOverride() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      controlId,
      applicability,
      justification,
    }: {
      controlId: number;
      applicability: Applicability;
      justification: string;
    }) => euAiActApi.setOverride(controlId, applicability, justification),
    onSuccess: () => invalidateApplicability(queryClient),
  });
}

export function useClearArticleOverride() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (controlId: number) => euAiActApi.clearOverride(controlId),
    onSuccess: () => invalidateApplicability(queryClient),
  });
}
