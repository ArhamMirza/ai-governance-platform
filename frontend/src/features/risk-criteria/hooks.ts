import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type RiskCriteriaUpdate, riskCriteriaApi } from "./api";

export const riskCriteriaKey = ["risk-criteria"];

/** Summaries embed the criteria they scored with, so they must refetch too. */
function invalidateScoredViews(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: riskCriteriaKey });
  queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  queryClient.invalidateQueries({ queryKey: ["risk-portfolio-summary"] });
}

export function useRiskCriteria() {
  return useQuery({ queryKey: riskCriteriaKey, queryFn: riskCriteriaApi.get });
}

export function useUpdateRiskCriteria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskCriteriaUpdate) => riskCriteriaApi.update(data),
    onSuccess: () => invalidateScoredViews(queryClient),
  });
}

export function useResetRiskCriteria() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: riskCriteriaApi.reset,
    onSuccess: () => invalidateScoredViews(queryClient),
  });
}
