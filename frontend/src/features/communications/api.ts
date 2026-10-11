import { httpClient } from "../../shared/api/httpClient";
import type {
  Communication,
  CommunicationDetail,
  CommunicationInput,
  CommunicationRecord,
  CommunicationRecordInput,
  CommunicationUpdateInput,
} from "./types";

export const communicationsApi = {
  list: () => httpClient.get<Communication[]>("/communications"),
  get: (id: number) => httpClient.get<CommunicationDetail>(`/communications/${id}`),
  create: (data: CommunicationInput) =>
    httpClient.post<CommunicationDetail>("/communications", data),
  update: (id: number, data: CommunicationUpdateInput) =>
    httpClient.put<CommunicationDetail>(`/communications/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/communications/${id}`),
  record: (id: number, data: CommunicationRecordInput) =>
    httpClient.post<CommunicationRecord>(`/communications/${id}/records`, data),
  removeRecord: (recordId: number) =>
    httpClient.delete<void>(`/communications/records/${recordId}`),
};
