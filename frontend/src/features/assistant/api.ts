import { httpClient } from "../../shared/api/httpClient";

export type RecordType =
  | "Policy"
  | "Procedure"
  | "ImpactAssessment"
  | "AISystem"
  | "DataInventory"
  | "RiskItem"
  | "Evidence";

export interface Conversation {
  id: number;
  title: string;
  context_entity_type: RecordType | null;
  context_entity_id: number | null;
  created_at: string;
  updated_at: string;
}

/** A source an answer cited, checked on the server against what was
 * actually retrieved for that turn before it was allowed through.
 *
 * "Tool" is not a governance record: it marks a citation as the result of a
 * structured lookup (an exact count or list from the database) rather than
 * a passage retrieval found. It is rendered the same as any other citation
 * -- numbered, linked, checked -- so a reader never has to tell them apart
 * to trust one. */
export interface Citation {
  n: number;
  chunk_id: number;
  source_type: RecordType | "Tool";
  source_id: number;
  title: string;
  section: string | null;
  read_by_ocr: boolean;
  entity_type: RecordType | "Tool";
  entity_id: number;
  href: string | null;
  download_evidence_id: number | null;
  excerpt: string;
  injection_findings: string[];
}

export interface CoverageGap {
  evidence_id: number;
  filename: string;
  detail: string | null;
}

export interface AssistantMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  /** Source numbers the model cited without having been given them. Already
   * removed from `content`; kept so the reader can be told it happened. */
  fabricated_citations: number[] | null;
  injection_findings: string[] | null;
  coverage_gaps: CoverageGap[] | null;
  retrieval_mode: "hybrid" | "keyword" | null;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: AssistantMessage[];
}

export interface ConversationStart {
  context_entity_type?: RecordType;
  context_entity_id?: number;
}

const BASE = "/assistant/conversations";

export const assistantApi = {
  list: () => httpClient.get<Conversation[]>(BASE),
  start: (data: ConversationStart) => httpClient.post<Conversation>(BASE, data),
  get: (id: number) => httpClient.get<ConversationDetail>(`${BASE}/${id}`),
  ask: (id: number, question: string) =>
    httpClient.post<AssistantMessage>(`${BASE}/${id}/messages`, { question }),
  remove: (id: number) => httpClient.delete<void>(`${BASE}/${id}`),
  /** Ask the server to load its models now, before anyone's first question. */
  warm: () => httpClient.post<void>("/assistant/warm"),
};
