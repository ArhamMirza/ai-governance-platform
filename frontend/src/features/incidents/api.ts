import { httpClient } from "../../shared/api/httpClient";
import type { Incident, IncidentCreateInput, IncidentUpdateInput } from "./types";

export const incidentsApi = {
  list: () => httpClient.get<Incident[]>("/ai-incidents"),
  get: (id: number) => httpClient.get<Incident>(`/ai-incidents/${id}`),
  create: (data: IncidentCreateInput) => httpClient.post<Incident>("/ai-incidents", data),
  update: (id: number, data: IncidentUpdateInput) =>
    httpClient.put<Incident>(`/ai-incidents/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/ai-incidents/${id}`),
};
