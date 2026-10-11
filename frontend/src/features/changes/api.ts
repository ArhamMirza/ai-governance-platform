import { httpClient } from "../../shared/api/httpClient";
import type {
  Change,
  ChangeAsOf,
  ChangeInput,
  ChangeStatusInput,
  ChangeUpdateInput,
} from "./types";

export const changesApi = {
  list: (aiSystemRowId?: number) =>
    httpClient.get<Change[]>(
      aiSystemRowId === undefined ? "/changes" : `/changes?ai_system_row_id=${aiSystemRowId}`,
    ),
  standingAsOf: (asOf: string) => httpClient.get<ChangeAsOf[]>(`/changes/standing?as_of=${asOf}`),
  get: (id: number) => httpClient.get<Change>(`/changes/${id}`),
  create: (data: ChangeInput) => httpClient.post<Change>("/changes", data),
  update: (id: number, data: ChangeUpdateInput) => httpClient.put<Change>(`/changes/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/changes/${id}`),
  setStatus: (id: number, data: ChangeStatusInput) =>
    httpClient.post<Change>(`/changes/${id}/status`, data),
  setAISystems: (id: number, aiSystemRowIds: number[]) =>
    httpClient.put<Change>(`/changes/${id}/ai-systems`, { ai_system_row_ids: aiSystemRowIds }),
};
