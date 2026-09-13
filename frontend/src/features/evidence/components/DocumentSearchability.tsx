import type { Evidence } from "../types";

/**
 * Says whether the assistant can read a document, when the answer is no.
 *
 * Deliberately silent on the ordinary case. What it will not do is stay
 * silent on a failure: a document that could not be indexed is invisible to
 * search but present in the record, and nobody would otherwise know that
 * asking about it returns nothing for the wrong reason.
 */
export function DocumentSearchability({ doc }: { doc: Evidence }) {
  const findings = doc.injection_findings ?? [];
  const unsearchable = doc.index_status !== "indexed" && doc.index_status !== "pending";
  const readByOcr = doc.index_status === "indexed" && /OCR/i.test(doc.index_detail ?? "");

  if (!unsearchable && findings.length === 0 && !readByOcr) return null;

  return (
    <div className="document-index-note">
      {unsearchable && (
        <span className="document-index-warning" role="status">
          Not searchable by the assistant{doc.index_detail ? ` — ${doc.index_detail}` : ""}
        </span>
      )}
      {readByOcr && <span className="document-index-hint">{doc.index_detail}</span>}
      {findings.length > 0 && (
        <span className="document-index-warning" role="status">
          This document contains text written to instruct an AI ({findings[0]}
          {findings.length > 1 ? `, +${findings.length - 1} more` : ""}). It is quoted to the
          assistant as data, not followed — worth a look.
        </span>
      )}
    </div>
  );
}
