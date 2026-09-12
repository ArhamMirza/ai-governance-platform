import { httpClient } from "../../shared/api/httpClient";
import type { Policy, PolicyCreateInput, PolicyHistoryEntry, PolicyUpdateInput } from "./types";

export const policiesApi = {
  list: () => httpClient.get<Policy[]>("/policies"),
  get: (id: number) => httpClient.get<Policy>(`/policies/${id}`),
  create: (data: PolicyCreateInput) => httpClient.post<Policy>("/policies", data),
  update: (id: number, data: PolicyUpdateInput) =>
    httpClient.put<Policy>(`/policies/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/policies/${id}`),
  submitForReview: (id: number) => httpClient.post<Policy>(`/policies/${id}/submit-for-review`),
  approve: (id: number) => httpClient.post<Policy>(`/policies/${id}/approve`),
  retire: (id: number) => httpClient.post<Policy>(`/policies/${id}/retire`),
  listVersions: (id: number) => httpClient.get<PolicyHistoryEntry[]>(`/policies/${id}/versions`),
};
