import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { httpClient } from "../../shared/api/httpClient";
import { impactAssessmentKey, useInvalidateImpactAssessments } from "./hooks";
import type { ImpactAssessment } from "./types";

/** One field a model proposed for the assessment. */
export interface DraftProposal {
  key: string;
  section: "narrative" | "factor";
  field: string;
  factor: string | null;
  label: string;
  value: string | number | null;
  /** For a proposed score, the one-sentence reason given for it. */
  rationale: string | null;
  citations: number[];
  /** What the records were missing, where they didn't support drafting it. */
  gap: string | null;
  /** Proposed without citing any source: shown, but flagged for scrutiny. */
  uncited: boolean;
  /** Every source it cited was invented, so no text is offered at all. */
  withheld: boolean;
}

export interface DraftSource {
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

export interface AssessmentDraft {
  id: number;
  status: string;
  provider: string;
  model: string;
  requested_by: number | null;
  created_at: string;
  proposals: DraftProposal[];
  sources: DraftSource[];
  injection_findings: string[] | null;
  coverage_gaps: { evidence_id: number; filename: string; detail: string | null }[] | null;
}

export interface AcceptedField {
  key: string;
  value: string | number;
}

const base = (assessmentId: number) => `/impact-assessments/${assessmentId}/ai-drafts`;

export const assessmentDraftApi = {
  generate: (assessmentId: number, instructions?: string) =>
    httpClient.post<AssessmentDraft>(base(assessmentId), { instructions: instructions || null }),
  latest: (assessmentId: number) =>
    httpClient.get<AssessmentDraft | null>(`${base(assessmentId)}/latest`),
  apply: (assessmentId: number, draftId: number, accepted: AcceptedField[]) =>
    httpClient.post<ImpactAssessment>(`${base(assessmentId)}/${draftId}/apply`, { accepted }),
  discard: (assessmentId: number, draftId: number) =>
    httpClient.post<void>(`${base(assessmentId)}/${draftId}/discard`),
};

export const draftKey = (assessmentId: number) =>
  [...impactAssessmentKey(assessmentId), "ai-draft"] as const;

/** The draft still waiting for a decision. Survives a page reload, so a long
 * review isn't lost to navigating away. */
export function useLatestAssessmentDraft(assessmentId: number, enabled: boolean) {
  return useQuery({
    queryKey: draftKey(assessmentId),
    queryFn: () => assessmentDraftApi.latest(assessmentId),
    enabled,
  });
}

export function useGenerateAssessmentDraft(assessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (instructions?: string) => assessmentDraftApi.generate(assessmentId, instructions),
    onSuccess: (draft) => queryClient.setQueryData(draftKey(assessmentId), draft),
  });
}

export function useApplyAssessmentDraft(riskAssessmentId: number | null, assessmentId: number) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateImpactAssessments(riskAssessmentId, assessmentId);
  return useMutation({
    mutationFn: ({ draftId, accepted }: { draftId: number; accepted: AcceptedField[] }) =>
      assessmentDraftApi.apply(assessmentId, draftId, accepted),
    onSuccess: () => {
      queryClient.setQueryData(draftKey(assessmentId), null);
      // Applying writes through the same paths as editing by hand, and can
      // withdraw an approval -- so everything an edit refreshes, this does too.
      invalidate();
    },
  });
}

export function useDiscardAssessmentDraft(assessmentId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: number) => assessmentDraftApi.discard(assessmentId, draftId),
    onSuccess: () => queryClient.setQueryData(draftKey(assessmentId), null),
  });
}
