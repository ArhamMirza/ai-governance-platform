import { httpClient } from "../../shared/api/httpClient";
import type { AIRole } from "./types";

export const aiRolesApi = {
  list: () => httpClient.get<AIRole[]>("/ai-roles"),
};
