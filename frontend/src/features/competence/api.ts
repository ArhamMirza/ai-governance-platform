import { httpClient } from "../../shared/api/httpClient";
import type {
  CompetenceRecord,
  CompetenceRecordInput,
  CompetenceRequirement,
  CompetenceRequirementInput,
  CompetenceRequirementSummary,
} from "./types";

export const competenceApi = {
  list: () => httpClient.get<CompetenceRequirementSummary[]>("/competence/requirements"),
  get: (id: number) => httpClient.get<CompetenceRequirement>(`/competence/requirements/${id}`),
  create: (data: CompetenceRequirementInput & { title: string }) =>
    httpClient.post<CompetenceRequirement>("/competence/requirements", data),
  update: (id: number, data: CompetenceRequirementInput) =>
    httpClient.put<CompetenceRequirement>(`/competence/requirements/${id}`, data),
  remove: (id: number) => httpClient.delete<void>(`/competence/requirements/${id}`),
  recordCompletion: (id: number, data: CompetenceRecordInput) =>
    httpClient.post<CompetenceRecord>(`/competence/requirements/${id}/records`, data),
  removeRecord: (recordId: number) => httpClient.delete<void>(`/competence/records/${recordId}`),
};
