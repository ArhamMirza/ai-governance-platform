import { useFrameworkMapping } from "../hooks";
import type { TaggedItem } from "../types";

const FRAMEWORK_LABELS: Record<string, string> = {
  iso_42001: "ISO 42001",
  eu_ai_act: "EU AI Act",
};

function TaggedItemChips({ items }: { items: TaggedItem[] }) {
  if (items.length === 0) {
    return <span className="framework-tags-empty">Not tagged to anything yet.</span>;
  }
  return (
    <div className="framework-tag-chips">
      {items.map((item) => (
        <span key={`${item.entity_type}-${item.entity_id}`} className="framework-tag-chip">
          {item.entity_type}: {item.label}
        </span>
      ))}
    </div>
  );
}

export function ClauseMappingTable() {
  const { data: entries, isLoading, isError } = useFrameworkMapping();

  if (isLoading) return <p>Loading clause mapping...</p>;
  if (isError || !entries) return <p>Failed to load clause mapping.</p>;

  // Annex A controls get their own Statement of Applicability tab -- this
  // view is just the main-body clauses and EU AI Act articles.
  const clauses = entries.filter((entry) => entry.category === "clause");

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Framework</th>
            <th>Code</th>
            <th>Title</th>
            <th>Tagged Items</th>
          </tr>
        </thead>
        <tbody>
          {clauses.map((entry) => (
            <tr key={entry.id}>
              <td>{FRAMEWORK_LABELS[entry.framework] ?? entry.framework}</td>
              <td>{entry.code}</td>
              <td>{entry.title}</td>
              <td>
                <TaggedItemChips items={entry.tagged_items} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
