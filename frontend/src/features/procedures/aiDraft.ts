import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { httpClient } from "../../shared/api/httpClient";
import { procedureKey, proceduresKey } from "./hooks";
import type { Procedure } from "./types";

/** One field the model proposed for the procedure. */
export interface ProcedureDraftProposal {
  key: string;
  section: string;
  field: string;
  label: string;
  value: string | null;
  citations: number[];
  /** What the records were missing, where they didn't support drafting it. */
  gap: string | null;
  /** Proposed without citing any source: shown, but flagged for scrutiny. */
  uncited: boolean;
  /** Every source it cited was invented, so no text is offered at all. */
  withheld: boolean;
}

export interface ProcedureDraftSource {
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

export interface ProcedureDraft {
  id: number;
  status: string;
  provider: string;
  model: string;
  requested_by: number | null;
  created_at: string;
  proposals: ProcedureDraftProposal[];
  sources: ProcedureDraftSource[];
  injection_findings: string[] | null;
  coverage_gaps: { evidence_id: number; filename: string; detail: string | null }[] | null;
}

export interface AcceptedProcedureField {
  key: string;
  value: string;
}

const base = (procedureId: number) => `/procedures/${procedureId}/ai-draft`;

export const procedureDraftApi = {
  generate: (procedureId: number, instructions?: string) =>
    httpClient.post<ProcedureDraft>(base(procedureId), { instructions: instructions || null }),
  latest: (procedureId: number) =>
    httpClient.get<ProcedureDraft | null>(`${base(procedureId)}/latest`),
  apply: (procedureId: number, draftId: number, accepted: AcceptedProcedureField[]) =>
    httpClient.post<Procedure>(`${base(procedureId)}/${draftId}/apply`, { accepted }),
  discard: (procedureId: number, draftId: number) =>
    httpClient.post<void>(`${base(procedureId)}/${draftId}/discard`),
};

const draftKey = (procedureId: number) => [...procedureKey(procedureId), "ai-draft"] as const;

/** The draft still waiting for a decision. Survives a page reload, so a
 * long review isn't lost to navigating away. */
export function useLatestProcedureDraft(procedureId: number, enabled: boolean) {
  return useQuery({
    queryKey: draftKey(procedureId),
    queryFn: () => procedureDraftApi.latest(procedureId),
    enabled,
  });
}

export function useGenerateProcedureDraft(procedureId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (instructions?: string) => procedureDraftApi.generate(procedureId, instructions),
    onSuccess: (draft) => queryClient.setQueryData(draftKey(procedureId), draft),
  });
}

export function useApplyProcedureDraft(procedureId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draftId, accepted }: { draftId: number; accepted: AcceptedProcedureField[] }) =>
      procedureDraftApi.apply(procedureId, draftId, accepted),
    onSuccess: () => {
      queryClient.setQueryData(draftKey(procedureId), null);
      // Applying writes through the same path as editing by hand -- refresh
      // everything an edit would.
      queryClient.invalidateQueries({ queryKey: proceduresKey });
      queryClient.invalidateQueries({ queryKey: procedureKey(procedureId) });
      queryClient.invalidateQueries({ queryKey: ["audit-log", "Procedure", procedureId] });
    },
  });
}

export function useDiscardProcedureDraft(procedureId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (draftId: number) => procedureDraftApi.discard(procedureId, draftId),
    onSuccess: () => queryClient.setQueryData(draftKey(procedureId), null),
  });
}
