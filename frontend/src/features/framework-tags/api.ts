import { httpClient } from "../../shared/api/httpClient";
import type { FrameworkControl } from "../framework-controls/types";

export const frameworkTagsApi = {
  get: (entityType: string, entityId: number) =>
    httpClient.get<FrameworkControl[]>(
      `/framework-tags?entity_type=${encodeURIComponent(entityType)}&entity_id=${entityId}`,
    ),
  set: (entityType: string, entityId: number, controlIds: number[]) =>
    httpClient.put<FrameworkControl[]>(
      `/framework-tags?entity_type=${encodeURIComponent(entityType)}&entity_id=${entityId}`,
      { control_ids: controlIds },
    ),
};
