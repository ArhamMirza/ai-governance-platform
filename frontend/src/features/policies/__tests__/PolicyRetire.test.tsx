import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditLogApi } from "../../audit-log/api";
import { useCanApprove } from "../../audit-log/useCanApprove";
import { evidenceApi, folderApi } from "../../evidence/api";
import { policiesApi } from "../api";
import { PolicyDetail } from "../components/PolicyDetail";
import type { Policy } from "../types";

vi.mock("../api");
vi.mock("../../evidence/api");
vi.mock("../../audit-log/api");
vi.mock("../../audit-log/useCanApprove");

function policy(status: Policy["status"]): Policy {
  return {
    id: 1,
    title: "Data Retention Policy",
    description: null,
    status,
    version: 1,
    owner_id: null,
    effective_date: null,
    next_review_date: status === "approved" ? "2027-01-01" : null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function renderDetail(status: Policy["status"], canApprove: boolean) {
  vi.mocked(policiesApi.get).mockResolvedValue(policy(status));
  vi.mocked(policiesApi.listVersions).mockResolvedValue([]);
  vi.mocked(folderApi.list).mockResolvedValue([]);
  vi.mocked(evidenceApi.list).mockResolvedValue([]);
  vi.mocked(auditLogApi.list).mockResolvedValue([]);
  vi.mocked(useCanApprove).mockReturnValue({
    canApprove,
    reason: canApprove ? null : "Only the Chief AI Governance Officer can approve.",
  });

  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PolicyDetail policyId={1} />
    </QueryClientProvider>,
  );
}

describe("retiring a policy", () => {
  it("offers Retire on an approved policy to someone who can approve", async () => {
    renderDetail("approved", true);

    const button = await screen.findByRole("button", { name: "Retire Policy" });
    await userEvent.click(button);

    await waitFor(() => expect(policiesApi.retire).toHaveBeenCalledWith(1));
  });

  it("does not offer Retire to someone who can't approve", async () => {
    renderDetail("approved", false);

    await screen.findByText("Data Retention Policy");
    expect(screen.queryByRole("button", { name: "Retire Policy" })).not.toBeInTheDocument();
  });

  it("does not offer Retire before a policy is approved", async () => {
    renderDetail("draft", true);

    await screen.findByText("Data Retention Policy");
    expect(screen.queryByRole("button", { name: "Retire Policy" })).not.toBeInTheDocument();
  });
});
