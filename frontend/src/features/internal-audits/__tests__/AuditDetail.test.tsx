import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { evidenceApi, folderApi } from "../../evidence/api";
import { usersApi } from "../../users/api";
import { auditFindingsApi, internalAuditsApi } from "../api";
import { AuditDetail } from "../components/AuditDetail";
import type { AuditFinding, InternalAudit } from "../types";

vi.mock("../api");
vi.mock("../../evidence/api");
vi.mock("../../users/api");

const audit: InternalAudit = {
  id: 1,
  audit_program_id: 1,
  title: "Q1 Risk Register Audit",
  planned_date: "2026-01-01",
  conducted_date: null,
  auditor_id: null,
  scope: null,
  conclusion: null,
  status: "in_progress",
  overdue: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const openFinding: AuditFinding = {
  id: 9,
  internal_audit_id: 1,
  description: "Risk items were closed without evidence attached.",
  finding_type: "nonconformity",
  corrective_action_ids: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function LocationProbe() {
  const location = useLocation();
  const state = location.state as
    | { sourceType: string; sourceId: number; nonconformityDescription: string }
    | null;
  return (
    <div>
      <p>Corrective actions page</p>
      {state && (
        <p>
          from {state.sourceType} #{state.sourceId}: {state.nonconformityDescription}
        </p>
      )}
    </div>
  );
}

function renderWithProviders() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/audit-programs/1/audits/1"]}>
        <Routes>
          <Route
            path="/audit-programs/:programId/audits/:auditId"
            element={<AuditDetail programId={1} auditId={1} />}
          />
          <Route path="/corrective-actions" element={<LocationProbe />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AuditDetail", () => {
  it("raises a corrective action from an unresolved finding, carrying its description", async () => {
    vi.mocked(internalAuditsApi.get).mockResolvedValue(audit);
    vi.mocked(auditFindingsApi.list).mockResolvedValue([openFinding]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(usersApi.directory).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders();

    await waitFor(() => {
      expect(screen.getByText(openFinding.description)).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Raise Corrective Action" }));

    expect(await screen.findByText("Corrective actions page")).toBeInTheDocument();
    expect(
      screen.getByText(`from AuditFinding #9: ${openFinding.description}`),
    ).toBeInTheDocument();
  });

  it("links to the existing corrective action instead of offering to raise a new one", async () => {
    vi.mocked(internalAuditsApi.get).mockResolvedValue(audit);
    vi.mocked(auditFindingsApi.list).mockResolvedValue([
      { ...openFinding, corrective_action_ids: [42] },
    ]);
    vi.mocked(evidenceApi.list).mockResolvedValue([]);
    vi.mocked(folderApi.list).mockResolvedValue([]);
    vi.mocked(usersApi.directory).mockResolvedValue([]);

    renderWithProviders();

    const link = await screen.findByRole("link", { name: "View corrective action" });
    expect(link).toHaveAttribute("href", "/corrective-actions/42");
    expect(screen.queryByRole("button", { name: "Raise Corrective Action" })).not.toBeInTheDocument();
  });
});
