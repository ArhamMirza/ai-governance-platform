import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditLogApi } from "../../audit-log/api";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { evidenceApi, folderApi } from "../../evidence/api";
import { frameworkTagsApi } from "../../framework-tags/api";
import { usersApi } from "../../users/api";
import { correctiveActionsApi } from "../api";
import { CorrectiveActionDetail } from "../components/CorrectiveActionDetail";
import type { CorrectiveAction } from "../types";

vi.mock("../api");
vi.mock("../../evidence/api");
vi.mock("../../audit-log/api");
vi.mock("../../audit-log/useCanApprove");
vi.mock("../../users/api");
vi.mock("../../framework-tags/api");

function baseCorrectiveAction(overrides: Partial<CorrectiveAction> = {}): CorrectiveAction {
  return {
    id: 1,
    title: "Resume screener ranking drift",
    nonconformity_description: "Model favors one demographic group.",
    root_cause: null,
    action_description: null,
    source_type: null,
    source_id: null,
    assignee_id: null,
    due_date: "2026-06-01",
    status: "open",
    overdue: false,
    framework_tags: [],
    closed_by: null,
    closed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function stubCommonApis() {
  vi.mocked(folderApi.list).mockResolvedValue([]);
  vi.mocked(evidenceApi.list).mockResolvedValue([]);
  vi.mocked(auditLogApi.list).mockResolvedValue([]);
  vi.mocked(usersApi.directory).mockResolvedValue([]);
  vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);
}

describe("CorrectiveActionDetail", () => {
  it("shows Start Work while open", async () => {
    stubCommonApis();
    vi.mocked(correctiveActionsApi.get).mockResolvedValue(baseCorrectiveAction());
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: false, reason: null });

    renderWithProviders(<CorrectiveActionDetail correctiveActionId={1} />);

    await waitFor(() => {
      expect(screen.getByText("Resume screener ranking drift")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Start Work" })).toBeInTheDocument();
  });

  it("shows Submit for Verification while in_progress", async () => {
    stubCommonApis();
    vi.mocked(correctiveActionsApi.get).mockResolvedValue(
      baseCorrectiveAction({ status: "in_progress" }),
    );
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: false, reason: null });

    renderWithProviders(<CorrectiveActionDetail correctiveActionId={1} />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Submit for Verification" }),
      ).toBeInTheDocument();
    });
  });

  it("shows the approval reason instead of Verify & Close when the viewer can't approve", async () => {
    stubCommonApis();
    vi.mocked(correctiveActionsApi.get).mockResolvedValue(
      baseCorrectiveAction({ status: "pending_verification" }),
    );
    vi.mocked(useCanApprove).mockReturnValue({
      canApprove: false,
      reason: "Only the Chief AI Governance Officer can approve.",
    });

    renderWithProviders(<CorrectiveActionDetail correctiveActionId={1} />);

    await waitFor(() => {
      expect(
        screen.getByText("Only the Chief AI Governance Officer can approve."),
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Verify & Close" })).not.toBeInTheDocument();
  });

  it("shows Verify & Close when the viewer can approve", async () => {
    stubCommonApis();
    vi.mocked(correctiveActionsApi.get).mockResolvedValue(
      baseCorrectiveAction({ status: "pending_verification" }),
    );
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: true, reason: null });

    renderWithProviders(<CorrectiveActionDetail correctiveActionId={1} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Verify & Close" })).toBeInTheDocument();
    });
  });

  it("shows Reopen and the overdue flag once closed and overdue", async () => {
    stubCommonApis();
    vi.mocked(correctiveActionsApi.get).mockResolvedValue(
      baseCorrectiveAction({ status: "closed", overdue: true }),
    );
    vi.mocked(useCanApprove).mockReturnValue({ canApprove: false, reason: null });

    renderWithProviders(<CorrectiveActionDetail correctiveActionId={1} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument();
    });
    expect(screen.getByText("Overdue")).toBeInTheDocument();
  });
});
