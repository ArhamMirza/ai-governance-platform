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

    render(<ClauseMappingTable />);

    expect(screen.getByText("5.2")).toBeInTheDocument();
    expect(screen.getByText("Policy: Data Retention Policy")).toBeInTheDocument();
  });

  it("excludes Annex A controls -- those live on the SoA tab", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: entries,
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable />);

    expect(screen.queryByText("A.2.2")).not.toBeInTheDocument();
  });

  it("shows a placeholder for untagged clauses", () => {
    vi.mocked(useFrameworkMapping).mockReturnValue({
      data: [{ ...entries[0], tagged_items: [] }],
      isLoading: false,
      isError: false,
    } as never);

    render(<ClauseMappingTable />);

    expect(screen.getByText("Not tagged to anything yet.")).toBeInTheDocument();
  });
});
