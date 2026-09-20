import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { httpClient } from "../../shared/api/httpClient";
import { riskAssessmentKey, riskAssessmentSheetKey } from "./hooks";
import type { RiskAssessment } from "./types";

/** One candidate risk item the model proposed, not yet added to the sheet. */
export interface RiskSuggestion {
  key: string;
  category: string | null;
  description: string | null;
  mitigation: string | null;
  likelihood: number | null;
  impact: number | null;
  citations: number[];
  /** What the records were missing, where they didn't support proposing it. */
  gap: string | null;
  /** Proposed without citing any source: shown, but flagged for scrutiny. */
  uncited: boolean;
  /** Every source it cited was invented, or it had no content at all. */
  withheld: boolean;
}

export interface RiskSuggestionSource {
  n: number;
  title: string;
  section: string | null;
  kind: string;
  href: string | null;
  download_evidence_id: number | null;
  read_by_ocr: boolean;
  excerpt: string;
  injection_findings: string[];
}

export interface RiskSuggestions {
  id: number;
  status: string;
  provider: string;
  model: string;
  requested_by: number | null;
  created_at: string;
  proposals: RiskSuggestion[];
  sources: RiskSuggestionSource[];
  injection_findings: string[] | null;
  coverage_gaps: { evidence_id: number; filename: string; detail: string | null }[] | null;
}

export interface AcceptedRiskItem {
  key: string;
  category: string;
  description: string;
  mitigation?: string | null;
  likelihood?: number | null;
  impact?: number | null;
  risk_owner?: string | null;
}

const base = (riskAssessmentId: number) =>
  `/risk-assessments/${riskAssessmentId}/ai-risk-suggestions`;

export const riskSuggestionsApi = {
  generate: (riskAssessmentId: number) =>
    httpClient.post<RiskSuggestions>(base(riskAssessmentId)),
  latest: (riskAssessmentId: number) =>
    httpClient.get<RiskSuggestions | null>(`${base(riskAssessmentId)}/latest`),
  apply: (riskAssessmentId: number, draftId: number, accepted: AcceptedRiskItem[]) =>
    httpClient.post<RiskAssessment>(`${base(riskAssessmentId)}/${draftId}/apply`, { accepted }),
  discard: (riskAssessmentId: number, draftId: number) =>
    httpClient.post<void>(`${base(riskAssessmentId)}/${draftId}/discard`),
};

export const riskSuggestionsKey = (riskAssessmentId: number) =>
  [...riskAssessmentKey(riskAssessmentId), "ai-risk-suggestions"] as const;

/** The suggestions still waiting for a decision. Survives a page reload, so
 * a long review isn't lost to navigating away. */
export function useLatestRiskSuggestions(riskAssessmentId: number, enabled: boolean) {
  return useQuery({
    queryKey: riskSuggestionsKey(riskAssessmentId),
    queryFn: () => riskSuggestionsApi.latest(riskAssessmentId),
    enabled,
  });
}

export function useGenerateRiskSuggestions(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => riskSuggestionsApi.generate(riskAssessmentId),
    onSuccess: (draft) => queryClient.setQueryData(riskSuggestionsKey(riskAssessmentId), draft),
  });
}

export function useApplyRiskSuggestions(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draftId, accepted }: { draftId: number; accepted: AcceptedRiskItem[] }) =>
      riskSuggestionsApi.apply(riskAssessmentId, draftId, accepted),
    onSuccess: () => {
      queryClient.setQueryData(riskSuggestionsKey(riskAssessmentId), null);
      // Applying adds rows through the same path as typing them, and can
      // withdraw the assessment's approval -- refresh what an edit would.
      queryClient.invalidateQueries({ queryKey: riskAssessmentSheetKey(riskAssessmentId) });
      queryClient.invalidateQueries({ queryKey: riskAssessmentKey(riskAssessmentId) });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["risk-portfolio-summary"] });
    },
  });
}

export function useDiscardRiskSuggestions(riskAssessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: number) => riskSuggestionsApi.discard(riskAssessmentId, draftId),
    onSuccess: () => queryClient.setQueryData(riskSuggestionsKey(riskAssessmentId), null),
  });
}
