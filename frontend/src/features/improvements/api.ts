import { httpClient } from "../../shared/api/httpClient";
import type {
  Improvement,
  ImprovementAsOf,
  ImprovementInput,
  ImprovementSourceType,
  ImprovementStatusInput,
  ImprovementUpdateInput,
} from "./types";

export const improvementsApi = {
  list: () => httpClient.get<Improvement[]>("/improvements"),
  listForSource: (sourceType: ImprovementSourceType, sourceId: number) =>
    httpClient.get<Improvement[]>(
      `/improvements?source_type=${sourceType}&source_id=${sourceId}`,
    ),
  standingAsOf: (asOf: string) =>
    httpClient.get<ImprovementAsOf[]>(`/improvements/standing?as_of=${asOf}`),
  get: (id: number) => httpClient.get<Improvement>(`/improvements/${id}`),
  create: (data: ImprovementInput) => httpClient.post<Improvement>("/improvements", data),
  update: (id: number, data: ImprovementUpdateInput) =>
    httpClient.put<Improvement>(`/improvements/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/improvements/${id}`),
  setStatus: (id: number, data: ImprovementStatusInput) =>
    httpClient.post<Improvement>(`/improvements/${id}/status`, data),
  carryOutAsChange: (id: number) =>
    httpClient.post<Improvement>(`/improvements/${id}/carry-out-as-change`, {}),
};
