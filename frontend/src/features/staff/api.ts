import { API_BASE_URL, httpClient } from "../../shared/api/httpClient";
import type { StaffLibraryItem } from "./types";

export const staffApi = {
  library: () => httpClient.get<StaffLibraryItem[]>("/staff/library"),
  documentUrl: (evidenceId: number) => `${API_BASE_URL}/staff/library/documents/${evidenceId}`,
};
