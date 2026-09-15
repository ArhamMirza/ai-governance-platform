import type { RecordType } from "./api";

export interface PageContext {
  entityType: RecordType;
  entityId: number;
  /** How the record is named in the panel's heading. */
  noun: string;
}

const PATTERNS: [RegExp, RecordType, string][] = [
  [/^\/policies\/(\d+)/, "Policy", "this policy"],
  [/^\/procedures\/(\d+)/, "Procedure", "this procedure"],
  [/^\/ai-systems\/(\d+)/, "AISystem", "this AI system"],
  [/^\/impact-assessments\/(\d+)/, "ImpactAssessment", "this impact assessment"],
];

/** The record on screen, if the current page is about one.
 *
 * A conversation started here is opened on that record, so the assistant
 * reads it directly and "this" means what the person is looking at. */
export function pageContextFor(pathname: string): PageContext | null {
  for (const [pattern, entityType, noun] of PATTERNS) {
    const match = pattern.exec(pathname);
    if (match) return { entityType, entityId: Number(match[1]), noun };
  }
  return null;
}
