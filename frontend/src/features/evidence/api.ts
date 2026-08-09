import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { Evidence, Folder } from "./types";

export const folderApi = {
  list: (entityType: string, entityId: number, parentFolderId: number | null) => {
    const params = new URLSearchParams({
      entity_type: entityType,
      entity_id: String(entityId),
    });
    if (parentFolderId !== null) params.set("parent_folder_id", String(parentFolderId));
    return httpClient.get<Folder[]>(`/folders?${params.toString()}`);
  },
  create: (entityType: string, entityId: number, name: string, parentFolderId: number | null) =>
    httpClient.post<Folder>("/folders", {
      entity_type: entityType,
      entity_id: entityId,
      name,
      parent_folder_id: parentFolderId,
    }),
  rename: (folderId: number, name: string) =>
    httpClient.put<Folder>(`/folders/${folderId}`, { name }),
  remove: (folderId: number) => httpClient.delete<void>(`/folders/${folderId}`),
};

export const evidenceApi = {
  list: (entityType: string, entityId: number, folderId: number | null) => {
    const params = new URLSearchParams({
      entity_type: entityType,
      entity_id: String(entityId),
    });
    if (folderId !== null) params.set("folder_id", String(folderId));
    return httpClient.get<Evidence[]>(`/evidence?${params.toString()}`);
  },
  upload: (
    entityType: string,
    entityId: number,
    folderId: number | null,
    file: File,
    description?: string,
  ) => {
    const formData = new FormData();
    formData.set("entity_type", entityType);
    formData.set("entity_id", String(entityId));
    if (folderId !== null) formData.set("folder_id", String(folderId));
    if (description) formData.set("description", description);
    formData.set("file", file);
    return httpClient.postForm<Evidence>("/evidence", formData);
  },
  remove: (evidenceId: number) => httpClient.delete<void>(`/evidence/${evidenceId}`),
  downloadUrl: (evidenceId: number) => `${API_BASE_URL}/evidence/${evidenceId}/download`,
};
