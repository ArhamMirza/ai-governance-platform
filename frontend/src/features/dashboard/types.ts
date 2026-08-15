export interface StatusCounts {
  total: number;
  by_status: Record<string, number>;
}

export interface AISystemSummary {
  total: number;
  by_risk_tier: Record<string, number>;
}

export interface RiskAssessmentSummary {
  total: number;
  by_status: Record<string, number>;
  high_risk_count: number;
}

export interface DashboardSummary {
  policies: StatusCounts;
  procedures: StatusCounts;
  ai_systems: AISystemSummary;
  risk_assessments: RiskAssessmentSummary;
}
