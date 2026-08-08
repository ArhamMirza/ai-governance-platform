import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { policiesApi } from "../api";
import { PolicyList } from "../components/PolicyList";
import type { Policy } from "../types";

vi.mock("../api");

const mockPolicy: Policy = {
  id: 1,
  title: "Data Retention Policy",
  description: null,
  status: "draft",
  version: 1,
  owner_id: null,
  content: "",
  effective_date: null,
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

describe("PolicyList", () => {
  it("renders policies returned from the API", async () => {
    vi.mocked(policiesApi.list).mockResolvedValue([mockPolicy]);

    renderWithProviders(<PolicyList />);

    await waitFor(() => {
      expect(screen.getByText("Data Retention Policy")).toBeInTheDocument();
    });
    expect(screen.getByText("draft")).toBeInTheDocument();
  });

  it("shows an empty state when there are no policies", async () => {
    vi.mocked(policiesApi.list).mockResolvedValue([]);

    renderWithProviders(<PolicyList />);

    await waitFor(() => {
      expect(screen.getByText("No policies yet.")).toBeInTheDocument();
    });
  });
});
