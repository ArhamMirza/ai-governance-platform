import { Fragment } from "react";

import { useFrameworkMapping } from "../hooks";
import type { FrameworkMappingEntry, TaggedItem } from "../types";

// ISO 42001 clauses 4-10 are numbered sub-clauses (4.1, 4.2, ...) under these
// top-level section titles -- shown as a header row so the table reads like
// the standard's own structure instead of a flat list.
const ISO_CLAUSE_SECTIONS: Record<string, string> = {
  "4": "Context of the organization",
  "5": "Leadership",
  "6": "Planning",
  "7": "Support",
  "8": "Operation",
  "9": "Performance evaluation",
  "10": "Improvement",
};

function leadingNumber(code: string): string {
  return code.split(".")[0];
}

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

interface ClauseMappingTableProps {
  framework: string;
}

export function ClauseMappingTable({ framework }: ClauseMappingTableProps) {
  const { data: entries, isLoading, isError } = useFrameworkMapping(framework);

  if (isLoading) return <p>Loading clause mapping...</p>;
  if (isError || !entries) return <p>Failed to load clause mapping.</p>;

  // Annex A controls get their own Statement of Applicability tab -- this
  // view is just the main-body clauses (or EU AI Act articles).
  const clauses = entries.filter((entry) => entry.category === "clause");
  const showSections = framework === "iso_42001";

  function renderRow(entry: FrameworkMappingEntry, index: number) {
    const sectionOf = (e: FrameworkMappingEntry) => (showSections ? leadingNumber(e.code) : null);
    const section = sectionOf(entry);
    const lastSection = index > 0 ? sectionOf(clauses[index - 1]) : null;
    const sectionHeader =
      section !== null && section !== lastSection && ISO_CLAUSE_SECTIONS[section] ? (
        <tr key={`section-${section}`} className="table-section-row">
          <td colSpan={3}>
            {section} &mdash; {ISO_CLAUSE_SECTIONS[section]}
          </td>
        </tr>
      ) : null;

    return (
      <Fragment key={entry.id}>
        {sectionHeader}
        <tr>
          <td data-type="code">{entry.code}</td>
          <td>{entry.title}</td>
          <td>
            <TaggedItemChips items={entry.tagged_items} />
          </td>
        </tr>
      </Fragment>
    );
  }

  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Title</th>
            <th>Tagged Items</th>
          </tr>
        </thead>
        <tbody>{clauses.map((entry, i) => renderRow(entry, i))}</tbody>
      </table>
    </div>
  );
}
