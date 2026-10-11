import type { FrameworkControl } from "../framework-controls/types";

export type CommunicationDirection = "internal" | "external";
export type CommunicationStatus = "active" | "retired";

export interface CommunicationRecord {
  id: number;
  communication_id: number;
  communicated_on: string;
  summary: string | null;
  recorded_by: number | null;
  created_at: string;
}

export interface Communication {
  id: number;
  topic: string;
  audience: string;
  direction: CommunicationDirection;
  method: string | null;
  responsible_id: number | null;
  notes: string | null;
  status: CommunicationStatus;
  interval_months: number | null;
  first_due: string | null;
  /** Computed by the server from the records, never stored. */
  last_communicated_on: string | null;
  next_due: string | null;
  overdue: boolean;
  framework_tags: FrameworkControl[];
  created_at: string;
  updated_at: string;
}

export interface CommunicationDetail extends Communication {
  /** Newest first. */
  records: CommunicationRecord[];
}

export interface CommunicationInput {
  topic: string;
  audience: string;
  direction: CommunicationDirection;
  method: string | null;
  responsible_id: number | null;
  notes: string | null;
  interval_months: number | null;
  first_due: string | null;
}

export type CommunicationUpdateInput = Partial<CommunicationInput> & {
  status?: CommunicationStatus;
};

export interface CommunicationRecordInput {
  communicated_on: string;
  summary: string | null;
}
