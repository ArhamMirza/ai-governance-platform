import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditLogApi } from "../../audit-log/api";
import { useCanApprove } from "../../audit-log/useCanApprove";
import type { SheetWithRows } from "../../sheets/types";
import { interestedPartiesAdapter, organizationContextApi, organizationIssuesAdapter } from "../api";
import { OrganizationContextDetail } from "../components/OrganizationContextDetail";
import type { OrganizationContext } from "../types";

vi.mock("../api");
vi.mock("../../audit-log/api");
vi.mock("../../audit-log/useCanApprove");
vi.mock("../../ai-roles/components/OrganizationAIRoles", () => ({
  OrganizationAIRoles: () => null,
}));
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: ({ entityType, entityId }: { entityType: string; entityId: number }) => (
    <p>{`Tags for ${entityType} ${entityId}`}</p>
  ),
}));

function context(overrides: Partial<OrganizationContext> = {}): OrganizationContext {
  return {
    id: 1,
    organization_description: "A resume-screening vendor.",
    ai_usage_overview: "Ranks applicants for human review.",
    ai_roles: [],
    aims_scope: null,
    aims_scope_exclusions: null,
    status: "draft",
    approved_by: null,
    approved_at: null,
    next_review_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function emptySheet(entityType: string, title: string): SheetWithRows {
  return {
    id: 1,
    entity_type: entityType,
    title,
    columns: [
      { key: "category", label: "Category", data_type: "text" },
      { key: "issue", label: "Issue", data_type: "text" },
    ],
    rows: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function renderDetail(overrides: Partial<OrganizationContext> = {}, canApprove = false) {
  vi.mocked(organizationContextApi.get).mockResolvedValue(context(overrides));
  vi.mocked(organizationIssuesAdapter.get).mockResolvedValue(
    emptySheet("OrganizationalIssues", "Internal and External Issues"),
  );
  vi.mocked(interestedPartiesAdapter.get).mockResolvedValue(
    emptySheet("InterestedParties", "Interested Parties"),
  );
  vi.mocked(auditLogApi.list).mockResolvedValue([]);
  vi.mocked(useCanApprove).mockReturnValue({
    canApprove,
    reason: canApprove ? null : "Only the Chief AI Governance Officer can approve.",
  });

  const queryClient = createTestQueryClient();
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <OrganizationContextDetail />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("OrganizationContextDetail", () => {
  it("renders the narrative fields and both tables", async () => {
    renderDetail();

    await waitFor(() => {
      expect(screen.getByLabelText("Organization description")).toHaveValue(
        "A resume-screening vendor.",
      );
      expect(screen.getByLabelText("Overall use of AI")).toHaveValue(
        "Ranks applicants for human review.",
      );
    });
    expect(screen.getByText("Internal and External Issues")).toBeInTheDocument();
    expect(screen.getByText("Interested Parties")).toBeInTheDocument();
  });

  it("saves an edited narrative field on blur, and only that field", async () => {
    renderDetail();
    vi.mocked(organizationContextApi.update).mockResolvedValue(context());

    const field = await screen.findByLabelText("Organization description");
    await userEvent.clear(field);
    await userEvent.type(field, "A hiring-technology company.");
    await userEvent.tab();

    await waitFor(() =>
      expect(organizationContextApi.update).toHaveBeenCalledWith({
        organization_description: "A hiring-technology company.",
      }),
    );
  });

  it("records the scope of the AI management system, saving only the field changed", async () => {
    renderDetail({ aims_scope: "All production AI systems." });
    vi.mocked(organizationContextApi.update).mockResolvedValue(context());

    expect(await screen.findByLabelText("What the AI management system covers")).toHaveValue(
      "All production AI systems.",
    );
    const exclusions = screen.getByLabelText("What is excluded, and why");
    await userEvent.type(exclusions, "Prototypes without customer data.");
    await userEvent.tab();

    await waitFor(() =>
      expect(organizationContextApi.update).toHaveBeenCalledWith({
        aims_scope_exclusions: "Prototypes without customer data.",
      }),
    );
  });

  it("clears a scope field to null when it's emptied", async () => {
    renderDetail({ aims_scope: "All production AI systems." });
    vi.mocked(organizationContextApi.update).mockResolvedValue(context());

    const scope = await screen.findByLabelText("What the AI management system covers");
    await userEvent.clear(scope);
    await userEvent.tab();

    await waitFor(() =>
      expect(organizationContextApi.update).toHaveBeenCalledWith({ aims_scope: null }),
    );
  });

  it("lets the context be tagged to the clauses it satisfies", async () => {
    renderDetail();

    expect(await screen.findByText("Tags for OrganizationContext 1")).toBeInTheDocument();
  });

  it("does not save on blur when nothing changed", async () => {
    renderDetail();

    const field = await screen.findByLabelText("Organization description");
    await userEvent.click(field);
    await userEvent.tab();

    expect(organizationContextApi.update).not.toHaveBeenCalled();
  });

  it("offers Submit for Review only in draft", async () => {
    renderDetail({ status: "draft" });

    expect(
      await screen.findByRole("button", { name: "Submit for Review" }),
    ).toBeInTheDocument();
  });

  it("offers Approve in review to someone who can approve", async () => {
    renderDetail({ status: "in_review" }, true);

    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
  });

  it("explains why someone who can't approve doesn't see the button", async () => {
    renderDetail({ status: "in_review" }, false);

    await waitFor(() => {
      expect(
        screen.getByText("Only the Chief AI Governance Officer can approve."),
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("warns that editing an approved record withdraws it", async () => {
    renderDetail({ status: "approved" });

    await waitFor(() => {
      expect(screen.getByText("Approved.")).toBeInTheDocument();
      expect(screen.getByText(/withdraws this approval/)).toBeInTheDocument();
    });
  });

  it("shows no withdrawal warning while still in draft", async () => {
    renderDetail({ status: "draft" });

    await screen.findByLabelText("Organization description");
    expect(screen.queryByText("Approved.")).not.toBeInTheDocument();
  });
});
