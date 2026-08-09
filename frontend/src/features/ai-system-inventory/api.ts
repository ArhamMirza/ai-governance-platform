import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { SheetApiAdapter, SheetColumn, SheetRow, SheetWithRows } from "../sheets/types";

export const aiSystemInventoryAdapter: SheetApiAdapter = {
  get: () => httpClient.get<SheetWithRows>("/ai-system-inventory"),
  setColumns: (columns: SheetColumn[]) =>
    httpClient.put<SheetWithRows>("/ai-system-inventory/columns", { columns }),
  addRow: (data) => httpClient.post<SheetRow>("/ai-system-inventory/rows", { data }),
  updateRow: (rowId, data) =>
    httpClient.put<SheetRow>(`/ai-system-inventory/rows/${rowId}`, { data }),
  deleteRow: (rowId) => httpClient.delete<void>(`/ai-system-inventory/rows/${rowId}`),
  upload: (file) => {
    const formData = new FormData();
    formData.set("file", file);
    return httpClient.postForm<SheetWithRows>("/ai-system-inventory/upload", formData);
  },
  exportUrl: () => `${API_BASE_URL}/ai-system-inventory/export`,
};
