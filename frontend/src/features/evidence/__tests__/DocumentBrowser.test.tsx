import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { useFrameworkControls } from "../../framework-controls/hooks";
import { useFrameworkTags, useSetFrameworkTags } from "../../framework-tags/hooks";
import { evidenceApi, folderApi } from "../api";
import { DocumentBrowser } from "../components/DocumentBrowser";
import type { Evidence, Folder } from "../types";

vi.mock("../api");
vi.mock("../../framework-tags/hooks");
vi.mock("../../framework-controls/hooks");

function renderBrowser() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <DocumentBrowser entityType="Policy" entityId={1} />
    </QueryClientProvider>,
  );
}

const rootFolder: Folder = {
  id: 10,
  entity_type: "Policy",
  entity_id: 1,
  parent_folder_id: null,
  name: "Signed Versions",
  created_at: "2026-01-01T00:00:00Z",
};

const rootDoc: Evidence = {
  id: 5,
  entity_type: "Policy",
  entity_id: 1,
  folder_id: null,
  filename: "policy.pdf",
  content_type: "application/pdf",
  size_bytes: 100,
  description: null,
  index_status: "indexed",
  index_detail: "1 passage(s) indexed.",
  injection_findings: null,
  uploaded_by: null,
  uploaded_at: "2026-01-01T00:00:00Z",
};

describe("DocumentBrowser", () => {
  it("renders folders and documents at the root level", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([rootFolder]);
    vi.mocked(evidenceApi.list).mockResolvedValue([rootDoc]);

    renderBrowser();

    await waitFor(() => {
      expect(screen.getByText(/Signed Versions/)).toBeInTheDocument();
      expect(screen.getByText("policy.pdf")).toBeInTheDocument();
    });
  });

  it("shows an empty state with no folders or documents", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);

    renderBrowser();

    await waitFor(() => {
      expect(screen.getByText("No documents yet.")).toBeInTheDocument();
    });
  });

  it("navigates into a folder and lists its contents", async () => {
    const subDoc: Evidence = { ...rootDoc, id: 6, folder_id: 10, filename: "signed-2026.pdf" };
    vi.mocked(folderApi.list).mockImplementation((_entityType, _entityId, parentFolderId) =>
      Promise.resolve(parentFolderId === null ? [rootFolder] : []),
    );
    vi.mocked(evidenceApi.list).mockImplementation((_entityType, _entityId, folderId) =>
      Promise.resolve(folderId === 10 ? [subDoc] : []),
    );
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText(/Signed Versions/)).toBeInTheDocument());

    await user.click(screen.getByText(/Signed Versions/));

    await waitFor(() => {
      expect(screen.getByText("signed-2026.pdf")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Signed Versions" })).toBeInTheDocument();
    });
  });

  it("creates a new folder", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(folderApi.create).mockResolvedValue(rootFolder);
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText("No documents yet.")).toBeInTheDocument());

    await user.type(screen.getByLabelText("New folder name"), "Signed Versions");
    await user.click(screen.getByRole("button", { name: "New Folder" }));

    await waitFor(() => {
      expect(folderApi.create).toHaveBeenCalledWith("Policy", 1, "Signed Versions", null);
    });
  });

  it("uploads a document", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.upload).mockResolvedValue(rootDoc);
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText("No documents yet.")).toBeInTheDocument());

    const file = new File(["hello"], "report.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Upload document"), file);

    await waitFor(() => {
      expect(evidenceApi.upload).toHaveBeenCalledWith("Policy", 1, null, file);
    });
  });

  it("shows an error when deleting a non-empty folder is rejected", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([rootFolder]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(folderApi.remove).mockRejectedValue(new ApiError(409, "Folder still has documents"));
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText(/Signed Versions/)).toBeInTheDocument());

    await user.click(screen.getAllByRole("button", { name: "Delete" })[0]);

    expect(await screen.findByRole("alert")).toHaveTextContent("Folder still has documents");
  });

  it("deletes a document", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([rootDoc]);
    vi.mocked(evidenceApi.remove).mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText("policy.pdf")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(evidenceApi.remove).toHaveBeenCalledWith(5);
    });
  });

  it("toggles an inline framework tag picker scoped to that evidence record", async () => {
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([rootDoc]);
    vi.mocked(useFrameworkTags).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useFrameworkControls).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);
    vi.mocked(useSetFrameworkTags).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as never);
    const user = userEvent.setup();

    renderBrowser();
    await waitFor(() => expect(screen.getByText("policy.pdf")).toBeInTheDocument());

    expect(screen.queryByText("No framework tags yet.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Tags" }));

    expect(screen.getByText("No framework tags yet.")).toBeInTheDocument();
    expect(useFrameworkTags).toHaveBeenCalledWith("Evidence", 5);
  });
});
