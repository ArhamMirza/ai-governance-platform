import { httpClient } from "../../shared/api/httpClient";
import type {
  Supplier,
  SupplierAISystemLinkInput,
  SupplierCreateInput,
  SupplierDetail,
  SupplierReview,
  SupplierReviewInput,
  SupplierRiskItem,
  SupplierUpdateInput,
} from "./types";

export const suppliersApi = {
  list: (aiSystemRowId?: number) =>
    httpClient.get<Supplier[]>(
      aiSystemRowId === undefined ? "/suppliers" : `/suppliers?ai_system_row_id=${aiSystemRowId}`,
    ),
  get: (id: number) => httpClient.get<SupplierDetail>(`/suppliers/${id}`),
  create: (data: SupplierCreateInput) => httpClient.post<SupplierDetail>("/suppliers", data),
  update: (id: number, data: SupplierUpdateInput) =>
    httpClient.put<SupplierDetail>(`/suppliers/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/suppliers/${id}`),
  setAISystems: (id: number, aiSystemRowIds: number[]) =>
    httpClient.put<SupplierDetail>(`/suppliers/${id}/ai-systems`, {
      ai_system_row_ids: aiSystemRowIds,
    }),
  updateAISystemLink: (id: number, aiSystemRowId: number, data: SupplierAISystemLinkInput) =>
    httpClient.put<SupplierDetail>(`/suppliers/${id}/ai-systems/${aiSystemRowId}`, data),
  listRiskItems: (id: number) => httpClient.get<SupplierRiskItem[]>(`/suppliers/${id}/risk-items`),
  recordReview: (id: number, data: SupplierReviewInput) =>
    httpClient.post<SupplierReview>(`/suppliers/${id}/reviews`, data),
  removeReview: (reviewId: number) => httpClient.delete<void>(`/suppliers/reviews/${reviewId}`),
};
