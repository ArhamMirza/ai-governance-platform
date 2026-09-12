import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { auditLogApi } from "../../audit-log/api";
import { evidenceApi, folderApi } from "../../evidence/api";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { policiesApi } from "../api";
import { PolicyDetail } from "../components/PolicyDetail";
import type { Policy, PolicyHistoryEntry } from "../types";

vi.mock("../api");
vi.mock("../../evidence/api");
vi.mock("../../audit-log/api");

const mockPolicy: Policy = {
  id: 1,
  title: "Data Retention Policy",
  description: "Governs how long we keep data",
  status: "draft",
  version: 2,
  owner_id: null,
  effective_date: null,
  next_review_date: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockHistory: PolicyHistoryEntry[] = [
  {
    action: "document_added",
    actor_id: null,
    timestamp: "2026-01-02T00:00:00Z",
    diff: { evidence_id: 1, filename: "policy-draft.pdf" },
  },
];

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("PolicyDetail", () => {
  it("renders policy info, version, history, and embeds the DocumentBrowser", async () => {
    vi.mocked(policiesApi.get).mockResolvedValue(mockPolicy);
    vi.mocked(policiesApi.listVersions).mockResolvedValue(mockHistory);
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(auditLogApi.list).mockResolvedValue([]);

    renderWithProviders(<PolicyDetail policyId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Data Retention Policy")).toBeInTheDocument();
      expect(screen.getByText("Version 2")).toBeInTheDocument();
    });

    expect(screen.getByText(/Document added.*policy-draft\.pdf/)).toBeInTheDocument();
    expect(screen.getByLabelText("Upload document")).toBeInTheDocument();
    expect(screen.getByLabelText("New folder name")).toBeInTheDocument();
  });
});
