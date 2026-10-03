import { httpClient } from "../../shared/api/httpClient";
import type {
  Measurement,
  MeasurementInput,
  Objective,
  ObjectiveAsOf,
  ObjectiveCloseInput,
  ObjectiveDetail,
  ObjectiveInput,
  ObjectiveUpdateInput,
} from "./types";

export const objectivesApi = {
  list: (aiSystemRowId?: number) =>
    httpClient.get<Objective[]>(
      aiSystemRowId === undefined
        ? "/objectives"
        : `/objectives?ai_system_row_id=${aiSystemRowId}`,
    ),
  standingAsOf: (asOf: string) =>
    httpClient.get<ObjectiveAsOf[]>(`/objectives/standing?as_of=${asOf}`),
  get: (id: number) => httpClient.get<ObjectiveDetail>(`/objectives/${id}`),
  create: (data: ObjectiveInput) => httpClient.post<ObjectiveDetail>("/objectives", data),
  update: (id: number, data: ObjectiveUpdateInput) =>
    httpClient.put<ObjectiveDetail>(`/objectives/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/objectives/${id}`),
  close: (id: number, data: ObjectiveCloseInput) =>
    httpClient.post<ObjectiveDetail>(`/objectives/${id}/close`, data),
  reopen: (id: number) => httpClient.post<ObjectiveDetail>(`/objectives/${id}/reopen`, {}),
  setAISystems: (id: number, aiSystemRowIds: number[]) =>
    httpClient.put<ObjectiveDetail>(`/objectives/${id}/ai-systems`, {
      ai_system_row_ids: aiSystemRowIds,
    }),
  recordMeasurement: (id: number, data: MeasurementInput) =>
    httpClient.post<Measurement>(`/objectives/${id}/measurements`, data),
  removeMeasurement: (measurementId: number) =>
    httpClient.delete<void>(`/objectives/measurements/${measurementId}`),
};
