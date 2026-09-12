import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { SheetApiAdapter, SheetColumn, SheetRow, SheetWithRows } from "../sheets/types";
import type { DataInventoryRecord } from "./types";

export const dataInventoryAdapter: SheetApiAdapter = {
  get: () => httpClient.get<SheetWithRows>("/data-inventory"),
  setColumns: (columns: SheetColumn[]) =>
    httpClient.put<SheetWithRows>("/data-inventory/columns", { columns }),
  addRow: (data) => httpClient.post<SheetRow>("/data-inventory/rows", { data }),
  updateRow: (rowId, data) =>
    httpClient.put<SheetRow>(`/data-inventory/rows/${rowId}`, { data }),
  deleteRow: (rowId) => httpClient.delete<void>(`/data-inventory/rows/${rowId}`),
  upload: (file) => {
    const formData = new FormData();
    formData.set("file", file);
    return httpClient.postForm<SheetWithRows>("/data-inventory/upload", formData);
  },
  exportUrl: () => `${API_BASE_URL}/data-inventory/export`,
};

export const dataInventoryReviewApi = {
  getRecord: (rowId: number) =>
    httpClient.get<DataInventoryRecord>(`/data-inventory/rows/${rowId}/record`),
  submitForApproval: (rowId: number) =>
    httpClient.post<DataInventoryRecord>(
      `/data-inventory/rows/${rowId}/submit-for-approval`,
    ),
  approve: (rowId: number) =>
    httpClient.post<DataInventoryRecord>(`/data-inventory/rows/${rowId}/approve`),
};
