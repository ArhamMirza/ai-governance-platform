import { useAuditLog } from "../hooks";

interface AuditLogViewerProps {
  entityType: string;
  /** Omit for the whole trail of this entity type -- see auditLogApi.list. */
  entityId?: number;
}

function formatDiff(diff: Record<string, unknown> | null): string {
  if (!diff || Object.keys(diff).length === 0) return "";
  return Object.entries(diff)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

export function AuditLogViewer({ entityType, entityId }: AuditLogViewerProps) {
  const { data: entries, isLoading, isError } = useAuditLog(entityType, entityId);

  if (isLoading) return <p>Loading audit log...</p>;
  if (isError) return <p>Failed to load audit log.</p>;
  if (!entries || entries.length === 0) return <p>No audit history yet.</p>;

  return (
    <ul>
      {entries.map((entry) => {
        const diffText = formatDiff(entry.diff);
        return (
          <li key={entry.id}>
            {entry.action} — {new Date(entry.timestamp).toLocaleString()}
            {diffText ? ` (${diffText})` : ""}
          </li>
        );
      })}
    </ul>
  );
}
