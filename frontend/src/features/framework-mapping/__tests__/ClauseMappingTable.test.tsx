import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ClauseMappingTable } from "../components/ClauseMappingTable";
import { useFrameworkMapping } from "../hooks";
import type { FrameworkMappingEntry } from "../types";

vi.mock("../hooks");

const entries: FrameworkMappingEntry[] = [
  {
    id: 1,
    framework: "iso_42001",
    code: "5.2",
    title: "AI policy",
    description: null,
    category: "clause",
    tagged_items: [{ entity_type: "Policy", entity_id: 3, label: "Data Retention Policy" }],
  },
  {
    id: 2,
    framework: "iso_42001",
    code: "A.2.2",
    title: "AI policy",
    description: null,
    category: "annex_a_control",
    tagged_items: [],
  },
];

describe("ClauseMappingTable", () => {
  it("shows clauses with their tagged items", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: entries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="iso_42001" />);

    expect(screen.getByText("5.2")).toBeInTheDocument();
    expect(screen.getByText("Policy: Data Retention Policy")).toBeInTheDocument();
  });

  it("scopes the query to the given framework", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: entries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="eu_ai_act" />);

    expect(useFrameworkMapping).toHaveBeenCalledWith("eu_ai_act");
  });

  it("excludes Annex A controls -- those live on the SoA tab", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: entries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="iso_42001" />);

    expect(screen.queryByText("A.2.2")).not.toBeInTheDocument();
  });

  it("shows a placeholder for untagged clauses", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: [{ ...entries[0], tagged_items: [] }],
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="iso_42001" />);

    expect(screen.getByText("Not tagged to anything yet.")).toBeInTheDocument();
  });

  it("groups ISO 42001 clauses under their top-level section", () => {
    const clauseEntries: FrameworkMappingEntry[] = [
      { ...entries[0], id: 10, code: "4.1", title: "Understanding the organization" },
      { ...entries[0], id: 11, code: "5.1", title: "Leadership and commitment" },
    ];
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: clauseEntries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="iso_42001" />);

    expect(screen.getByText("4 — Context of the organization")).toBeInTheDocument();
    expect(screen.getByText("Leadership and commitment")).toBeInTheDocument();
  });

  it("does not show section headers for the flat EU AI Act article list", () => {
    const euEntries: FrameworkMappingEntry[] = [
      { ...entries[0], id: 20, framework: "eu_ai_act", code: "Art.9", title: "Risk management" },
    ];
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: euEntries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable framework="eu_ai_act" />);

    expect(screen.getByText("Art.9")).toBeInTheDocument();
    expect(screen.queryByText(/Context of the organization/)).not.toBeInTheDocument();
  });
});
