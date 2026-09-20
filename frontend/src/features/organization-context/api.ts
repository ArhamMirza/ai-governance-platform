import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { SheetApiAdapter, SheetColumn, SheetWithRows } from "../sheets/types";
import type { OrganizationContext, OrganizationContextUpdateInput } from "./types";

const BASE = "/organization-context";

export const organizationContextApi = {
  get: () => httpClient.get<OrganizationContext>(BASE),
  update: (data: OrganizationContextUpdateInput) =>
    httpClient.put<OrganizationContext>(BASE, data),
  submitForReview: () => httpClient.post<OrganizationContext>(`${BASE}/submit-for-review`),
  approve: () => httpClient.post<OrganizationContext>(`${BASE}/approve`),
};

function makeSheetAdapter(sheetPath: "issues" | "interested-parties"): SheetApiAdapter {
  const sheetBase = `${BASE}/${sheetPath}-sheet`;
  const rowBase = `${BASE}/${sheetPath}`;
  return {
    get: () => httpClient.get<SheetWithRows>(sheetBase),
    setColumns: (columns: SheetColumn[]) =>
      httpClient.put<SheetWithRows>(`${sheetBase}/columns`, { columns }),
    addRow: (data) => httpClient.post(`${rowBase}`, { data }),
    updateRow: (rowId, data) => httpClient.put(`${rowBase}/${rowId}`, { data }),
    deleteRow: (rowId) => httpClient.delete(`${rowBase}/${rowId}`),
    upload: async (file: File) => {
      const formData = new FormData();
      formData.set("file", file);
      await httpClient.postForm(`${sheetBase}/upload`, formData);
      return httpClient.get<SheetWithRows>(sheetBase);
    },
    exportUrl: () => `${API_BASE_URL}${sheetBase}/export`,
  };
}

export const organizationIssuesAdapter = makeSheetAdapter("issues");
export const interestedPartiesAdapter = makeSheetAdapter("interested-parties");
