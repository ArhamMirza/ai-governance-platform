import { httpClient } from "../../shared/api/httpClient";
import type {
  AISystemLifecycle,
  DeploymentRecordInput,
  MonitoringInput,
} from "./types";

const base = (rowId: number) => `/ai-systems/${rowId}/lifecycle`;

export const aiSystemLifecycleApi = {
  get: (rowId: number) => httpClient.get<AISystemLifecycle>(base(rowId)),
  advance: (rowId: number) => httpClient.post<AISystemLifecycle>(`${base(rowId)}/advance`),
  revert: (rowId: number, reason: string) =>
    httpClient.post<AISystemLifecycle>(`${base(rowId)}/revert`, { reason }),
  setDeploymentRecord: (rowId: number, data: DeploymentRecordInput) =>
    httpClient.put<AISystemLifecycle>(`${base(rowId)}/deployment-record`, data),
  setMonitoring: (rowId: number, data: MonitoringInput) =>
    httpClient.put<AISystemLifecycle>(`${base(rowId)}/monitoring`, data),
  requestDeploymentApproval: (rowId: number) =>
    httpClient.post<AISystemLifecycle>(`${base(rowId)}/request-deployment-approval`),
  approveDeployment: (rowId: number) =>
    httpClient.post<AISystemLifecycle>(`${base(rowId)}/approve-deployment`),
};

/** Uploads a document carrying the document_type a stage gate looks for.
 * DocumentBrowser's own uploader stays untyped for ordinary evidence. */
export async function uploadStageDocument(
  rowId: number,
  documentType: string,
  file: File,
): Promise<void> {
  const formData = new FormData();
  formData.set("entity_type", "AISystem");
  formData.set("entity_id", String(rowId));
  formData.set("document_type", documentType);
  formData.set("file", file);
  await httpClient.postForm("/evidence", formData);
}
