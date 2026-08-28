import type { TaggedItem } from "../framework-mapping/types";

export interface FrameworkSoaEntry {
  id: number;
  framework: string;
  code: string;
  title: string;
  description: string | null;
  applicability: "applicable" | "not_applicable";
  justification: string | null;
  updated_at: string;
  tagged_items: TaggedItem[];
}

export interface FrameworkSoaEntryUpdate {
  applicability: string;
  justification: string | null;
}
