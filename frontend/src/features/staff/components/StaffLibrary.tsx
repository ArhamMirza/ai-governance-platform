import { staffApi } from "../api";
import { useStaffLibrary } from "../hooks";
import type { StaffLibraryItem } from "../types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const KIND_LABELS: Record<StaffLibraryItem["kind"], string> = {
  policy: "Policy",
  procedure: "Procedure",
};

/** The approved policies and procedures the organization has shared with
 * employees, with their documents. */
export function StaffLibrary() {
  const { data: items, isLoading, isError } = useStaffLibrary();

  if (isLoading) return <p>Loading policies and information...</p>;
  if (isError) return <p>Failed to load policies and information.</p>;
  if (!items || items.length === 0) {
    return <p>Nothing has been shared with you yet.</p>;
  }

  return (
    <ul className="staff-library">
      {items.map((item) => (
        <li key={`${item.kind}-${item.id}`}>
          <h3>{item.title}</h3>
          <p className="approval-note">
            {KIND_LABELS[item.kind]} · version {item.version}
            {item.effective_date && ` · in effect from ${item.effective_date}`}
          </p>
          {item.description && <p>{item.description}</p>}
          {item.documents.length > 0 && (
            <ul>
              {item.documents.map((document) => (
                <li key={document.id}>
                  <a href={staffApi.documentUrl(document.id)} download={document.filename}>
                    {document.filename}
                  </a>{" "}
                  <span className="approval-note">{formatSize(document.size_bytes)}</span>
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
}
