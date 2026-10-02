import { httpClient } from "../../shared/api/httpClient";
import type {
  Applicability,
  EuAiActApplicability,
  EuAiActApplicabilityInput,
  EuAiActArticle,
} from "./types";

export const euAiActApi = {
  getApplicability: () => httpClient.get<EuAiActApplicability>("/eu-ai-act/applicability"),
  updateApplicability: (data: EuAiActApplicabilityInput) =>
    httpClient.put<EuAiActApplicability>("/eu-ai-act/applicability", data),
  listArticles: () => httpClient.get<EuAiActArticle[]>("/eu-ai-act/articles"),
  setOverride: (controlId: number, applicability: Applicability, justification: string) =>
    httpClient.put<EuAiActArticle[]>(`/eu-ai-act/articles/${controlId}/override`, {
      applicability,
      justification,
    }),
  clearOverride: (controlId: number) =>
    httpClient.delete<EuAiActArticle[]>(`/eu-ai-act/articles/${controlId}/override`),
};
