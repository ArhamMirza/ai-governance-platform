import { httpClient } from "../../shared/api/httpClient";
import type {
  ImpactAssessment,
  ImpactAssessmentCreateInput,
  ImpactAssessmentUpdateInput,
  ImpactFactorAssessment,
  ImpactFactorUpdateInput,
} from "./types";

export const impactAssessmentsApi = {
  listAll: () => httpClient.get<ImpactAssessment[]>("/impact-assessments"),
  listForRiskAssessment: (riskAssessmentId: number) =>
    httpClient.get<ImpactAssessment[]>(
      `/risk-assessments/${riskAssessmentId}/impact-assessments`,
    ),
  create: (riskAssessmentId: number, data: ImpactAssessmentCreateInput) =>
    httpClient.post<ImpactAssessment>(
      `/risk-assessments/${riskAssessmentId}/impact-assessments`,
      data,
    ),
  createForAISystem: (aiSystemRowId: number) =>
    httpClient.post<ImpactAssessment>("/impact-assessments", {
      ai_system_row_id: aiSystemRowId,
    }),
  get: (id: number) => httpClient.get<ImpactAssessment>(`/impact-assessments/${id}`),
  update: (id: number, data: ImpactAssessmentUpdateInput) =>
    httpClient.put<ImpactAssessment>(`/impact-assessments/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/impact-assessments/${id}`),
  updateFactor: (id: number, factor: string, data: ImpactFactorUpdateInput) =>
    httpClient.put<ImpactFactorAssessment>(
      `/impact-assessments/${id}/factors/${encodeURIComponent(factor)}`,
      data,
    ),
};
