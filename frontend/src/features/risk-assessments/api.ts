import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { SheetApiAdapter, SheetColumn, SheetRow, SheetWithRows } from "../sheets/types";
import type {
  RiskAssessment,
  RiskAssessmentCreateInput,
  RiskAssessmentUpdateInput,
  RiskPortfolioSummary,
} from "./types";

export const riskAssessmentsApi = {
  list: () => httpClient.get<RiskAssessment[]>("/risk-assessments"),
  summary: () => httpClient.get<RiskPortfolioSummary>("/risk-assessments/summary"),
  get: (id: number) => httpClient.get<RiskAssessment>(`/risk-assessments/${id}`),
  create: (data: RiskAssessmentCreateInput) =>
    httpClient.post<RiskAssessment>("/risk-assessments", data),
  update: (id: number, data: RiskAssessmentUpdateInput) =>
    httpClient.put<RiskAssessment>(`/risk-assessments/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/risk-assessments/${id}`),
  closeRiskItem: (riskAssessmentId: number, rowId: number) =>
    httpClient.post<SheetRow>(`/risk-assessments/${riskAssessmentId}/rows/${rowId}/close`),
  submitForOwnerApproval: (id: number) =>
    httpClient.post<RiskAssessment>(`/risk-assessments/${id}/submit-for-owner-approval`),
  approveOwnerStage: (id: number) =>
    httpClient.post<RiskAssessment>(`/risk-assessments/${id}/approve-owner-stage`),
  approveCaigoStage: (id: number) =>
    httpClient.post<RiskAssessment>(`/risk-assessments/${id}/approve-caigo-stage`),
};

export function makeRiskAssessmentSheetAdapter(riskAssessmentId: number): SheetApiAdapter {
  const base = `/risk-assessments/${riskAssessmentId}`;
  return {
    get: () => httpClient.get<SheetWithRows>(`${base}/sheet`),
    setColumns: async (columns: SheetColumn[]) => {
      await httpClient.put(`${base}/columns`, { columns });
      return httpClient.get<SheetWithRows>(`${base}/sheet`);
    },
    addRow: (data) => httpClient.post<SheetRow>(`${base}/rows`, { data }),
    updateRow: (rowId, data) => httpClient.put<SheetRow>(`${base}/rows/${rowId}`, { data }),
    deleteRow: (rowId) => httpClient.delete<void>(`${base}/rows/${rowId}`),
    upload: async (file) => {
      const formData = new FormData();
      formData.set("file", file);
      await httpClient.postForm(`${base}/upload`, formData);
      return httpClient.get<SheetWithRows>(`${base}/sheet`);
    },
    exportUrl: () => `${API_BASE_URL}${base}/export`,
  };
}
