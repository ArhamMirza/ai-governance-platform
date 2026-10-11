import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { auditLogApi } from "../../audit-log/api";
import { evidenceApi, folderApi } from "../../evidence/api";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { proceduresApi } from "../api";
import { ProcedureDetail } from "../components/ProcedureDetail";
import type { Procedure, ProcedureHistoryEntry } from "../types";

vi.mock("../api");
vi.mock("../../evidence/api");
vi.mock("../../audit-log/api");

const mockProcedure: Procedure = {
  id: 1,
  title: "Model Validation Procedure",
  description: "Validates models before deployment",
  status: "draft",
  version: 2,
  owner_id: null,
  policy_id: null,
  effective_date: null,
  next_review_date: null,
  shared_with_employees: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockHistory: ProcedureHistoryEntry[] = [
  {
    action: "document_added",
    actor_id: null,
    timestamp: "2026-01-02T00:00:00Z",
    diff: { evidence_id: 1, filename: "procedure-draft.pdf" },
  },
];

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ProcedureDetail", () => {
  it("renders procedure info, version, history, and embeds the DocumentBrowser", async () => {
    vi.mocked(proceduresApi.get).mockResolvedValue(mockProcedure);
    vi.mocked(proceduresApi.listVersions).mockResolvedValue(mockHistory);
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(auditLogApi.list).mockResolvedValue([]);

    renderWithProviders(<ProcedureDetail procedureId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Model Validation Procedure")).toBeInTheDocument();
      expect(screen.getByText("Version 2")).toBeInTheDocument();
    });

    expect(screen.getByText(/Document added.*procedure-draft\.pdf/)).toBeInTheDocument();
    expect(screen.getByLabelText("Upload document")).toBeInTheDocument();
  });
});
