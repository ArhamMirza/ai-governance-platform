import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { aiSystemInventoryAdapter } from "../ai-system-inventory/api";
import { riskAssessmentsApi } from "./api";
import type { RiskAssessmentCreateInput, RiskAssessmentUpdateInput } from "./types";

const riskAssessmentsKey = ["risk-assessments"] as const;
export const riskAssessmentKey = (id: number) => ["risk-assessments", id] as const;

export function riskAssessmentSheetKey(id: number) {
  return ["risk-assessments", id, "sheet"] as const;
}

export function useRiskAssessments() {
  return useQuery({ queryKey: riskAssessmentsKey, queryFn: riskAssessmentsApi.list });
}

export function useRiskPortfolioSummary() {
  return useQuery({
    queryKey: ["risk-portfolio-summary"],
    queryFn: riskAssessmentsApi.summary,
  });
}

export function useRiskAssessment(id: number) {
  return useQuery({ queryKey: riskAssessmentKey(id), queryFn: () => riskAssessmentsApi.get(id) });
}

export function useCreateRiskAssessment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskAssessmentCreateInput) => riskAssessmentsApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: riskAssessmentsKey }),
  });
}

export function useUpdateRiskAssessment(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RiskAssessmentUpdateInput) => riskAssessmentsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskAssessmentsKey });
      queryClient.invalidateQueries({ queryKey: riskAssessmentKey(id) });
    },
  });
}

export function useAISystemInventoryRows() {
  return useQuery({ queryKey: ["ai-system-inventory"], queryFn: aiSystemInventoryAdapter.get });
}

export function useCloseRiskItem(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (rowId: number) => riskAssessmentsApi.closeRiskItem(riskAssessmentId, rowId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: riskAssessmentSheetKey(riskAssessmentId) });
      queryClient.invalidateQueries({ queryKey: ["risk-portfolio-summary"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({
        queryKey: ["audit-log", "RiskAssessment", riskAssessmentId],
      });
    },
  });
}
