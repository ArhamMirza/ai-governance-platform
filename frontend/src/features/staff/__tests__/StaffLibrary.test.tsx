import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { staffApi } from "../api";
import { ShareWithEmployees } from "../components/ShareWithEmployees";
import { StaffLibrary } from "../components/StaffLibrary";
import type { StaffLibraryItem } from "../types";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { staffApi: { ...actual.staffApi, library: vi.fn() } };
});

function renderLibrary() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <StaffLibrary />
    </QueryClientProvider>,
  );
}

const retentionPolicy: StaffLibraryItem = {
  kind: "policy",
  id: 1,
  title: "Data Retention Policy",
  description: "How long we keep personal and model data.",
  version: 2,
  effective_date: "2026-03-01",
  documents: [
    { id: 11, filename: "retention-v2.pdf", content_type: "application/pdf", size_bytes: 2048 },
    { id: 12, filename: "faq.pdf", content_type: "application/pdf", size_bytes: 900 },
  ],
};

describe("StaffLibrary", () => {
  it("lists each shared item with its version, date and documents", async () => {
    vi.mocked(staffApi.library).mockResolvedValue([
      retentionPolicy,
      {
        kind: "procedure",
        id: 5,
        title: "Reporting an AI concern",
        description: null,
        version: 1,
        effective_date: null,
        documents: [],
      },
    ]);

    renderLibrary();

    expect(await screen.findByText("Data Retention Policy")).toBeInTheDocument();
    expect(screen.getByText("Policy · version 2 · in effect from 2026-03-01")).toBeInTheDocument();
    expect(screen.getByText("How long we keep personal and model data.")).toBeInTheDocument();
    expect(screen.getByText("Reporting an AI concern")).toBeInTheDocument();
    expect(screen.getByText("Procedure · version 1")).toBeInTheDocument();
  });

  it("links each document to the employee download, not the internal one", async () => {
    vi.mocked(staffApi.library).mockResolvedValue([retentionPolicy]);

    renderLibrary();

    const link = await screen.findByRole("link", { name: "retention-v2.pdf" });
    expect(link.getAttribute("href")).toMatch(/\/staff\/library\/documents\/11$/);
    expect(link.getAttribute("href")).not.toMatch(/\/evidence\//);
    expect(screen.getByText("2 KB")).toBeInTheDocument();
    expect(screen.getByText("900 B")).toBeInTheDocument();
  });

  it("says when nothing has been shared yet", async () => {
    vi.mocked(staffApi.library).mockResolvedValue([]);

    renderLibrary();

    expect(await screen.findByText("Nothing has been shared with you yet.")).toBeInTheDocument();
  });
});

describe("ShareWithEmployees", () => {
  it("reports the new choice, and says when it only takes effect on approval", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <ShareWithEmployees shared={false} approved={false} pending={false} onChange={onChange} />,
    );

    expect(screen.getByText(/once it's approved/)).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Share with employees" }));
    expect(onChange).toHaveBeenCalledWith(true);

    rerender(<ShareWithEmployees shared approved pending={false} onChange={onChange} />);
    expect(screen.queryByText(/once it's approved/)).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Share with employees" })).toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: "Share with employees" }));
    expect(onChange).toHaveBeenLastCalledWith(false);
  });

  it("can't be changed while a save is in flight", () => {
    render(<ShareWithEmployees shared approved pending onChange={vi.fn()} />);

    expect(screen.getByRole("checkbox", { name: "Share with employees" })).toBeDisabled();
  });
});
