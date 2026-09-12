import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { proceduresApi } from "../api";
import { ProcedureList } from "../components/ProcedureList";
import type { Procedure } from "../types";

vi.mock("../api");

const mockProcedure: Procedure = {
  id: 1,
  title: "Model Validation Procedure",
  description: null,
  status: "draft",
  version: 1,
  owner_id: null,
  policy_id: null,
  effective_date: null,
  next_review_date: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProcedureList", () => {
  it("renders procedures returned from the API", async () => {
    vi.mocked(proceduresApi.list).mockResolvedValue([mockProcedure]);

    renderWithProviders(<ProcedureList />);

    await waitFor(() => {
      expect(screen.getByText("Model Validation Procedure")).toBeInTheDocument();
    });
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("shows an empty state when there are no procedures", async () => {
    vi.mocked(proceduresApi.list).mockResolvedValue([]);

    renderWithProviders(<ProcedureList />);

    await waitFor(() => {
      expect(screen.getByText("No procedures yet.")).toBeInTheDocument();
    });
  });
});
