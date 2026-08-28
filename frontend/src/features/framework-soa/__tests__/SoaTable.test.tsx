import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { SoaTable } from "../components/SoaTable";
import { useFrameworkSoa, useUpdateFrameworkSoaEntry } from "../hooks";
import type { FrameworkSoaEntry } from "../types";

vi.mock("../hooks");

const entries: FrameworkSoaEntry[] = [
  {
    id: 5,
    framework: "iso_42001",
    code: "A.2.2",
    title: "AI policy",
    description: null,
    applicability: "applicable",
    justification: null,
    updated_at: "2026-01-01T00:00:00Z",
    tagged_items: [],
  },
];

function mockHooks(mutateAsync = vi.fn()) {
  vi.mocked(useFrameworkSoa).mockReturnValue({
    data: entries,
    isLoading: false,
    isError: false,
  } as never);
  vi.mocked(useUpdateFrameworkSoaEntry).mockReturnValue({
    mutateAsync,
    isPending: false,
  } as never);
  return mutateAsync;
}

describe("SoaTable", () => {
  it("lists each Annex A control with its applicability", () => {
    mockHooks();

    render(<SoaTable />);

    expect(screen.getByText("A.2.2")).toBeInTheDocument();
    expect(screen.getByLabelText("Applicability for A.2.2")).toHaveValue("applicable");
  });

  it("saves a new applicability immediately on change", async () => {
    const mutateAsync = mockHooks();
    const user = userEvent.setup();

    render(<SoaTable />);
    await user.selectOptions(screen.getByLabelText("Applicability for A.2.2"), "not_applicable");

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        controlId: 5,
        data: { applicability: "not_applicable", justification: null },
      });
    });
  });

  it("saves the justification on blur", async () => {
    const mutateAsync = mockHooks();
    const user = userEvent.setup();

    render(<SoaTable />);
    const textarea = screen.getByLabelText("Justification for A.2.2");
    await user.type(textarea, "Handled by our vendor contract.");
    await user.tab();

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        controlId: 5,
        data: { applicability: "applicable", justification: "Handled by our vendor contract." },
      });
    });
  });
});
