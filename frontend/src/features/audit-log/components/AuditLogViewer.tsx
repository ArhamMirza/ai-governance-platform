import { useAuditLog } from "../hooks";

interface AuditLogViewerProps {
  entityType: string;
  /** Omit for the whole trail of this entity type -- see auditLogApi.list. */
  entityId?: number;
  /** The heading on the disclosure. Some trails are not "the audit log" --
   * the data inventory keeps a separate review history alongside one. */
  title?: string;
}

function formatDiff(diff: Record<string, unknown> | null): string {
  if (!diff || Object.keys(diff).length === 0) return "";
  return Object.entries(diff)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

/**
 * An entity's trail, collapsed.
 *
 * The trail matters for an audit and almost never while someone is doing the
 * work, so it ships closed with its entry count on the summary: the page says
 * a record is traceable without spending half a screen proving it. Opening it
 * is one click, and the disclosure owns its own heading so every page shows
 * the trail the same way.
 */
export function AuditLogViewer({
  entityType,
  entityId,
  title = "Audit log",
}: AuditLogViewerProps) {
  const { data: entries, isLoading, isError } = useAuditLog(entityType, entityId);

  if (isLoading) return <p className="audit-log-status">Loading audit log...</p>;
  if (isError) return <p className="audit-log-status">Failed to load audit log.</p>;

  const count = entries?.length ?? 0;

  return (
    <details className="audit-log">
      <summary>
        {/* A real heading, not a span -- so "Audit log" (or a title like
           "Review history") still shows up when a screen-reader user
           navigates a page by its headings, the way every page's own <h3>
           used to before it moved in here. */}
        <h3 className="audit-log-heading">{title}</h3>
        <span className="audit-log-count">{count}</span>
      </summary>
      {count === 0 ? (
        <p className="audit-log-status">No audit history yet.</p>
      ) : (
        <ul className="audit-log-list">
          {entries?.map((entry) => {
            const diffText = formatDiff(entry.diff);
            return (
              <li key={entry.id}>
                {entry.action} — {new Date(entry.timestamp).toLocaleString()}
                {diffText ? ` (${diffText})` : ""}
              </li>
            );
          })}
        </ul>
      )}
    </details>
  );
}
