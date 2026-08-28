import { httpClient } from "../../shared/api/httpClient";
import type { FrameworkSoaEntry, FrameworkSoaEntryUpdate } from "./types";

export const frameworkSoaApi = {
  list: () => httpClient.get<FrameworkSoaEntry[]>("/framework-soa"),
  update: (controlId: number, data: FrameworkSoaEntryUpdate) =>
    httpClient.put<FrameworkSoaEntry>(`/framework-soa/${controlId}`, data),
};
