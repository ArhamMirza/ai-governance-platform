import { httpClient } from "../../shared/api/httpClient";
import type { FrameworkControl } from "./types";

export const frameworkControlsApi = {
  list: (framework?: string) =>
    httpClient.get<FrameworkControl[]>(
      framework ? `/framework-controls?framework=${encodeURIComponent(framework)}` : "/framework-controls",
    ),
};
