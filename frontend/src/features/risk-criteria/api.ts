import { httpClient } from "../../shared/api/httpClient";
import type { RiskCriteria } from "../risk-assessments/riskSeverity";

export interface RiskCriteriaUpdate {
  medium_min_score: number;
  high_min_score: number;
}

export const riskCriteriaApi = {
  get: () => httpClient.get<RiskCriteria>("/risk-criteria"),
  update: (data: RiskCriteriaUpdate) => httpClient.put<RiskCriteria>("/risk-criteria", data),
  reset: () => httpClient.post<RiskCriteria>("/risk-criteria/reset", {}),
};
