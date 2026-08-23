/**
 * Mirrors the backend's canonical bands (app/core/risk_scoring.py). The server
 * returns the criteria it scored with alongside every summary, so prefer those
 * over the defaults here whenever they are available.
 */

export interface RiskCriteria {
  medium_min_score: number;
  high_min_score: number;
  is_default: boolean;
  min_score: number;
  max_score: number;
  updated_at: string | null;
}

export const DEFAULT_MEDIUM_MIN_SCORE = 5;
export const DEFAULT_HIGH_MIN_SCORE = 13;

export const DEFAULT_BANDS = {
  medium_min_score: DEFAULT_MEDIUM_MIN_SCORE,
  high_min_score: DEFAULT_HIGH_MIN_SCORE,
};

export type Severity = "low" | "medium" | "high";

export interface Bands {
  medium_min_score: number;
  high_min_score: number;
}

export function severityForScore(score: number, bands: Bands = DEFAULT_BANDS): Severity {
  if (score >= bands.high_min_score) return "high";
  if (score >= bands.medium_min_score) return "medium";
  return "low";
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};
