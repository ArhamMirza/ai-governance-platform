import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { impactAssessmentsApi } from "./api";
import type {
  ImpactAssessmentCreateInput,
  ImpactAssessmentUpdateInput,
  ImpactFactorUpdateInput,
} from "./types";

export const allImpactAssessmentsKey = ["impact-assessments"] as const;

export function impactAssessmentsKey(riskAssessmentId: number) {
  return ["risk-assessments", riskAssessmentId, "impact-assessments"] as const;
}

export function impactAssessmentKey(impactAssessmentId: number) {
  return ["impact-assessments", impactAssessmentId] as const;
}

/** An impact assessment can be worked on before any risk assessment exists
 * for its AI system, so every mutation refreshes the global list and only
 * additionally refreshes a risk assessment's list when viewed from one. */
function useInvalidateImpactAssessments(
  riskAssessmentId: number | null,
  impactAssessmentId?: number,
) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: allImpactAssessmentsKey });
    if (riskAssessmentId !== null) {
      queryClient.invalidateQueries({ queryKey: impactAssessmentsKey(riskAssessmentId) });
    }
    if (impactAssessmentId !== undefined) {
      queryClient.invalidateQueries({ queryKey: impactAssessmentKey(impactAssessmentId) });
    }
  };
}

export function useAllImpactAssessments() {
  return useQuery({
    queryKey: allImpactAssessmentsKey,
    queryFn: impactAssessmentsApi.listAll,
  });
}

export function useImpactAssessment(impactAssessmentId: number) {
  return useQuery({
    queryKey: impactAssessmentKey(impactAssessmentId),
    queryFn: () => impactAssessmentsApi.get(impactAssessmentId),
  });
}

export function useImpactAssessments(riskAssessmentId: number) {
  return useQuery({
    queryKey: impactAssessmentsKey(riskAssessmentId),
    queryFn: () => impactAssessmentsApi.listForRiskAssessment(riskAssessmentId),
  });
}

export function useCreateImpactAssessment(riskAssessmentId: number) {
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId);
  return useMutation({
    mutationFn: (data: ImpactAssessmentCreateInput = {}) =>
      impactAssessmentsApi.create(riskAssessmentId, data),
    onSuccess: invalidate,
  });
}

export function useCreateImpactAssessmentForAISystem() {
  const invalidate = useInvalidateImpactAssessments(null);
  return useMutation({
    mutationFn: (aiSystemRowId: number) =>
      impactAssessmentsApi.createForAISystem(aiSystemRowId),
    onSuccess: invalidate,
  });
}

export function useUpdateImpactAssessment(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId, impactAssessmentId);
  return useMutation({
    mutationFn: (data: ImpactAssessmentUpdateInput) =>
      impactAssessmentsApi.update(impactAssessmentId, data),
    onSuccess: invalidate,
  });
}

export function useDeleteImpactAssessment(riskAssessmentId: number | null) {
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId);
  return useMutation({
    mutationFn: (impactAssessmentId: number) => impactAssessmentsApi.remove(impactAssessmentId),
    onSuccess: invalidate,
  });
}

export function useUpdateImpactFactor(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId, impactAssessmentId);
  return useMutation({
    mutationFn: ({ factor, data }: { factor: string; data: ImpactFactorUpdateInput }) =>
      impactAssessmentsApi.updateFactor(impactAssessmentId, factor, data),
    onSuccess: invalidate,
  });
}

function useInvalidateImpactAssessmentApproval(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId, impactAssessmentId);
  const queryClient = useQueryClient();
  return () => {
    invalidate();
    queryClient.invalidateQueries({
      queryKey: ["audit-log", "ImpactAssessmentOwnerApproval", impactAssessmentId],
    });
    queryClient.invalidateQueries({
      queryKey: ["audit-log", "ImpactAssessmentCaigoApproval", impactAssessmentId],
    });
  };
}

export function useSubmitImpactAssessmentForOwnerApproval(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessmentApproval(riskAssessmentId, impactAssessmentId);
  return useMutation({
    mutationFn: () => impactAssessmentsApi.submitForOwnerApproval(impactAssessmentId),
    onSuccess: invalidate,
  });
}

export function useApproveImpactAssessmentOwnerStage(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessmentApproval(riskAssessmentId, impactAssessmentId);
  return useMutation({
    mutationFn: () => impactAssessmentsApi.approveOwnerStage(impactAssessmentId),
    onSuccess: invalidate,
  });
}

export function useApproveImpactAssessmentCaigoStage(
  riskAssessmentId: number | null,
  impactAssessmentId: number,
) {
  const invalidate = useInvalidateImpactAssessmentApproval(riskAssessmentId, impactAssessmentId);
  return useMutation({
    mutationFn: () => impactAssessmentsApi.approveCaigoStage(impactAssessmentId),
    onSuccess: invalidate,
  });
}
