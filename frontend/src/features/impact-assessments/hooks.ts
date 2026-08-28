import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { impactAssessmentsApi } from "./api";
import type {
  ImpactAssessmentCreateInput,
  ImpactAssessmentUpdateInput,
  ImpactFactorUpdateInput,
} from "./types";

export function impactAssessmentsKey(riskAssessmentId: number) {
  return ["risk-assessments", riskAssessmentId, "impact-assessments"] as const;
}

export function useImpactAssessments(riskAssessmentId: number) {
  return useQuery({
    queryKey: impactAssessmentsKey(riskAssessmentId),
    queryFn: () => impactAssessmentsApi.listForRiskAssessment(riskAssessmentId),
  });
}

export function useCreateImpactAssessment(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImpactAssessmentCreateInput = {}) =>
      impactAssessmentsApi.create(riskAssessmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: impactAssessmentsKey(riskAssessmentId) });
    },
  });
}

export function useUpdateImpactAssessment(riskAssessmentId: number, impactAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ImpactAssessmentUpdateInput) =>
      impactAssessmentsApi.update(impactAssessmentId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: impactAssessmentsKey(riskAssessmentId) });
    },
  });
}

export function useDeleteImpactAssessment(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (impactAssessmentId: number) => impactAssessmentsApi.remove(impactAssessmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: impactAssessmentsKey(riskAssessmentId) });
    },
  });
}

export function useUpdateImpactFactor(riskAssessmentId: number, impactAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ factor, data }: { factor: string; data: ImpactFactorUpdateInput }) =>
      impactAssessmentsApi.updateFactor(impactAssessmentId, factor, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: impactAssessmentsKey(riskAssessmentId) });
    },
  });
}
