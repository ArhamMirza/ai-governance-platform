import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { authApi } from "../../auth/api";
import { auditLogApi } from "../../audit-log/api";
import { evidenceApi, folderApi } from "../../evidence/api";
import { policiesApi } from "../api";
import { PolicyDetail } from "../components/PolicyDetail";
import type { Policy } from "../types";

vi.mock("../api");
vi.mock("../../auth/api");
vi.mock("../../evidence/api");
vi.mock("../../audit-log/api");

const policy: Policy = {
  id: 1,
  title: "AI Acceptable Use",
  description: null,
  status: "approved",
  version: 1,
  owner_id: null,
  effective_date: null,
  next_review_date: null,
  shared_with_employees: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderAs(role: string) {
  vi.mocked(authApi.me).mockResolvedValue({
    id: 1,
    name: "Someone",
    email: "someone@example.com",
    role,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z", must_change_password: false, mfa_enabled: false, mfa_setup_required: false,
  });
  vi.mocked(policiesApi.get).mockResolvedValue(policy);
  vi.mocked(policiesApi.listVersions).mockResolvedValue([]);
  vi.mocked(folderApi.list).mockResolvedValue([]);
  vi.mocked(evidenceApi.list).mockResolvedValue([]);
  vi.mocked(auditLogApi.list).mockResolvedValue([]);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <PolicyDetail policyId={1} />
    </QueryClientProvider>,
  );
}

describe("sharing a policy with employees", () => {
  it("lets someone who can edit share an approved policy", async () => {
    vi.mocked(policiesApi.setSharing).mockResolvedValue({ ...policy, shared_with_employees: true });
    const user = userEvent.setup();
    renderAs("contributor");

    await user.click(await screen.findByRole("checkbox", { name: "Share with employees" }));

    expect(policiesApi.setSharing).toHaveBeenCalledWith(1, true);
  });

  it("is not offered to someone who can't edit", async () => {
    renderAs("viewer");

    await screen.findByText("AI Acceptable Use");
    expect(screen.queryByRole("checkbox", { name: "Share with employees" })).not.toBeInTheDocument();
  });
});
