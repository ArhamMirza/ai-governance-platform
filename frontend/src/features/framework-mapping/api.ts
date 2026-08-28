import { httpClient } from "../../shared/api/httpClient";
import type { FrameworkMappingEntry } from "./types";

export const frameworkMappingApi = {
  list: (framework?: string) =>
    httpClient.get<FrameworkMappingEntry[]>(
      framework ? `/framework-mapping?framework=${encodeURIComponent(framework)}` : "/framework-mapping",
    ),
};
