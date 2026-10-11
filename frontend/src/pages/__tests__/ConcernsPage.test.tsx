import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { concernsApi } from "../../features/concerns/api";
import { createTestQueryClient } from "../../test/testQueryClient";
import { ConcernDetailPage } from "../ConcernDetailPage";
import { ConcernsPage } from "../ConcernsPage";

vi.mock("../../features/concerns/api");
vi.mock("../../features/concerns/components/ConcernList", () => ({
  ConcernList: () => <p>the register</p>,
}));
vi.mock("../../features/concerns/components/ConcernSettingsPanel", () => ({
  ConcernSettingsPanel: () => <p>the settings</p>,
}));
vi.mock("../../features/concerns/components/ConcernDetail", () => ({
  ConcernDetail: ({ concernId }: { concernId: number }) => <p>{`detail ${concernId}`}</p>,
}));

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/concerns" element={<ConcernsPage />} />
          <Route path="/concerns/:concernId" element={<ConcernDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Concerns pages", () => {
  it("show the register and settings to someone who handles concerns", async () => {
    vi.mocked(concernsApi.access).mockResolvedValue({ can_handle: true });

    renderAt("/concerns");

    expect(await screen.findByText("the register")).toBeInTheDocument();
    expect(screen.getByText("the settings")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record a Concern" })).toBeInTheDocument();
  });

  it("show everyone else only that they can't read them", async () => {
    vi.mocked(concernsApi.access).mockResolvedValue({ can_handle: false });

    renderAt("/concerns");

    expect(await screen.findByText(/Only administrators can read and handle/)).toBeInTheDocument();
    expect(screen.queryByText("the register")).not.toBeInTheDocument();
  });

  it("open a concern for a handler, and refuse anyone else", async () => {
    vi.mocked(concernsApi.access).mockResolvedValue({ can_handle: true });
    const { unmount } = renderAt("/concerns/4");
    expect(await screen.findByText("detail 4")).toBeInTheDocument();
    unmount();

    vi.mocked(concernsApi.access).mockResolvedValue({ can_handle: false });
    renderAt("/concerns/4");
    expect(await screen.findByText("Only administrators can read concerns.")).toBeInTheDocument();
    expect(screen.queryByText("detail 4")).not.toBeInTheDocument();
  });
});
