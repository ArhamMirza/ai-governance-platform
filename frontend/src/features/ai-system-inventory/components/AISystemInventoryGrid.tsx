import { Link, useSearchParams } from "react-router-dom";

import { DataGrid } from "../../sheets/components/DataGrid";
import { aiSystemInventoryAdapter } from "../api";

// Server-owned: the stage only moves by passing a stage gate, so it is shown
// here rather than edited here.
const READ_ONLY_COLUMNS = ["lifecycle_stage"];

const QUERY_KEY = ["ai-system-inventory"];
const LONG_TEXT_COLUMNS = [
  "description",
  "purpose",
  "resource_documentation",
  "data_resources",
  "tooling_frameworks",
  "tooling_documentation",
  "compute_infrastructure",
  "hosting_environment",
  "development_team",
  "oversight_roles",
];

/** The column a row is identified by. It is pinned into every view, because
 * a sheet of resource columns with no system name against them is unreadable. */
const IDENTITY_COLUMN = "name";

/**
 * The inventory carries the whole of Annex A.4 (resources for AI systems)
 * alongside the system's own description, which is far too many columns to
 * read at once. Each A.4 control gets its own view instead, addressable by
 * URL so a view can be linked to and bookmarked.
 */
interface SheetView {
  slug: string;
  label: string;
  /** The Annex A control this slice documents, where there is one. */
  note?: string;
  keys: string[];
}

const VIEWS: SheetView[] = [
  {
    slug: "overview",
    label: "System Overview",
    keys: ["name", "description", "purpose", "lifecycle_stage", "risk_tier"],
  },
  {
    slug: "resources",
    label: "Resource Documentation",
    note: "A.4.2 / A.4.3",
    keys: ["resource_documentation", "data_resources"],
  },
  {
    slug: "tooling",
    label: "Tooling",
    note: "A.4.4",
    keys: ["tooling_frameworks", "tooling_documentation"],
  },
  {
    slug: "computing",
    label: "System & Computing",
    note: "A.4.5",
    keys: ["compute_infrastructure", "hosting_environment"],
  },
  {
    slug: "people",
    label: "Human Resources",
    note: "A.4.6",
    keys: ["development_team", "oversight_roles"],
  },
];

// The identity column is pinned into every view (see IDENTITY_COLUMN below)
// rather than belonging to any one of them, so it's excluded here -- left
// in, "overview"'s group label would be applied to the name column on every
// other view too, since a group header is looked up by column key alone.
const COLUMN_GROUPS = VIEWS.map((view) => ({
  label: view.note ? `${view.label} (${view.note})` : view.label,
  keys: view.keys.filter((key) => key !== IDENTITY_COLUMN),
}));

const ALL_SLUG = "all";

export function AISystemInventoryGrid() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("view");
  const active = VIEWS.find((view) => view.slug === requested)?.slug ?? (requested === ALL_SLUG ? ALL_SLUG : VIEWS[0].slug);

  const selectView = (slug: string) => {
    const next = new URLSearchParams(searchParams);
    next.set("view", slug);
    // A view is a filter, not a step in a journey -- going back should leave
    // the page, not walk back through every column set that was looked at.
    setSearchParams(next, { replace: true });
  };

  const view = VIEWS.find((candidate) => candidate.slug === active);
  const visibleColumnKeys = view
    ? Array.from(new Set([IDENTITY_COLUMN, ...view.keys]))
    : undefined;

  return (
    <>
      <nav className="sheet-views" aria-label="Inventory columns">
        {VIEWS.map((candidate) => (
          <button
            key={candidate.slug}
            type="button"
            className={candidate.slug === active ? "active" : undefined}
            aria-current={candidate.slug === active ? "page" : undefined}
            onClick={() => selectView(candidate.slug)}
          >
            {candidate.label}
            {candidate.note && <span className="sheet-views-note">{candidate.note}</span>}
          </button>
        ))}
        <button
          type="button"
          className={active === ALL_SLUG ? "active" : undefined}
          aria-current={active === ALL_SLUG ? "page" : undefined}
          onClick={() => selectView(ALL_SLUG)}
        >
          All columns
        </button>
      </nav>

      <DataGrid
        queryKey={QUERY_KEY}
        adapter={aiSystemInventoryAdapter}
        longTextColumnKeys={LONG_TEXT_COLUMNS}
        columnGroups={COLUMN_GROUPS}
        visibleColumnKeys={visibleColumnKeys}
        readOnlyColumnKeys={READ_ONLY_COLUMNS}
        rowActions={(row) => <Link to={`/ai-systems/${row.id}`}>Open</Link>}
        confirmDelete={(row) => {
          const name =
            typeof row.data.name === "string" && row.data.name ? row.data.name : "this AI system";
          return `Deleting ${name} also deletes its impact assessment and risk assessment, including their risk items and evidence. This cannot be undone.`;
        }}
      />
    </>
  );
}
