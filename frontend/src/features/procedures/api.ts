import { httpClient } from "../../shared/api/httpClient";
import type {
  Procedure,
  ProcedureCreateInput,
  ProcedureHistoryEntry,
  ProcedureUpdateInput,
} from "./types";

export const proceduresApi = {
  list: () => httpClient.get<Procedure[]>("/procedures"),
  get: (id: number) => httpClient.get<Procedure>(`/procedures/${id}`),
  create: (data: ProcedureCreateInput) => httpClient.post<Procedure>("/procedures", data),
  update: (id: number, data: ProcedureUpdateInput) =>
    httpClient.put<Procedure>(`/procedures/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/procedures/${id}`),
  submitForReview: (id: number) =>
    httpClient.post<Procedure>(`/procedures/${id}/submit-for-review`),
  approve: (id: number) => httpClient.post<Procedure>(`/procedures/${id}/approve`),
  listVersions: (id: number) =>
    httpClient.get<ProcedureHistoryEntry[]>(`/procedures/${id}/versions`),
};
