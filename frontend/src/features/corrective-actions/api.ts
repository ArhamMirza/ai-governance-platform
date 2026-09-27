import { httpClient } from "../../shared/api/httpClient";
import type {
  CorrectiveAction,
  CorrectiveActionCreateInput,
  CorrectiveActionUpdateInput,
} from "./types";

export const correctiveActionsApi = {
  list: () => httpClient.get<CorrectiveAction[]>("/corrective-actions"),
  get: (id: number) => httpClient.get<CorrectiveAction>(`/corrective-actions/${id}`),
  create: (data: CorrectiveActionCreateInput) =>
    httpClient.post<CorrectiveAction>("/corrective-actions", data),
  update: (id: number, data: CorrectiveActionUpdateInput) =>
    httpClient.put<CorrectiveAction>(`/corrective-actions/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/corrective-actions/${id}`),
  submitForVerification: (id: number) =>
    httpClient.post<CorrectiveAction>(`/corrective-actions/${id}/submit-for-verification`),
  verifyAndClose: (id: number) =>
    httpClient.post<CorrectiveAction>(`/corrective-actions/${id}/verify-and-close`),
  reopen: (id: number) => httpClient.post<CorrectiveAction>(`/corrective-actions/${id}/reopen`),
};
