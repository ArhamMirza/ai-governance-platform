import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { euAiActApi } from "../api";
import { EuAiActApplicabilityPanel } from "../components/EuAiActApplicabilityPanel";
import { EuAiActArticleTable } from "../components/EuAiActArticleTable";
import type { EuAiActApplicability, EuAiActArticle } from "../types";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode) {
  return render(<QueryClientProvider client={createTestQueryClient()}>{ui}</QueryClientProvider>);
}

function makeApplicability(overrides: Partial<EuAiActApplicability> = {}): EuAiActApplicability {
  return {
    scope: "not_assessed",
    in_scope: null,
    scope_justification: null,
    is_provider: false,
    is_deployer: false,
    is_importer: false,
    is_distributor: false,
    has_high_risk_systems: null,
    high_risk_system_count: 2,
    suggested_roles: [],
    updated_by: null,
    updated_at: null,
    ...overrides,
  };
}

function makeArticle(overrides: Partial<EuAiActArticle> = {}): EuAiActArticle {
  return {
    id: 16,
    code: "Art.16",
    title: "Obligations of providers of high-risk AI systems",
    automatic_applicable: false,
    automatic_reason: "Applies to providers; your organization isn't recorded as one.",
    override_applicability: null,
    override_justification: null,
    applicable: false,
    reason: "Applies to providers; your organization isn't recorded as one.",
    ...overrides,
  };
}

describe("EuAiActApplicabilityPanel", () => {
  it("asks for roles and the high-risk question only once in scope", async () => {
    vi.mocked(euAiActApi.getApplicability).mockResolvedValue(makeApplicability());
    const user = userEvent.setup();

    renderWithProviders(<EuAiActApplicabilityPanel />);

    await user.click(await screen.findByLabelText("No, we're outside its scope"));
    expect(screen.getByLabelText("Why it doesn't apply")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Yes, we're in scope"));
    expect(screen.queryByLabelText("Why it doesn't apply")).not.toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
    expect(screen.getByText("2 systems in your inventory are tagged high risk.")).toBeInTheDocument();
  });

  it("saves an in-scope deployer assessment", async () => {
    vi.mocked(euAiActApi.getApplicability).mockResolvedValue(makeApplicability());
    vi.mocked(euAiActApi.updateApplicability).mockResolvedValue(makeApplicability());
    const user = userEvent.setup();

    renderWithProviders(<EuAiActApplicabilityPanel />);

    await user.click(await screen.findByLabelText("Yes, we're in scope"));
    await user.click(screen.getByRole("checkbox", { name: /Deployer/ }));
    await user.click(screen.getByLabelText("Yes"));
    await user.click(screen.getByRole("button", { name: "Save Assessment" }));

    expect(euAiActApi.updateApplicability).toHaveBeenCalledWith({
      in_scope: true,
      scope_justification: null,
      is_provider: false,
      is_deployer: true,
      is_importer: false,
      is_distributor: false,
      has_high_risk_systems: true,
    });
  });

  it("offers the roles the organization's AI roles point to, and ticks them on request", async () => {
    vi.mocked(euAiActApi.getApplicability).mockResolvedValue(
      makeApplicability({ suggested_roles: ["provider", "deployer"] }),
    );
    vi.mocked(euAiActApi.updateApplicability).mockResolvedValue(makeApplicability());
    const user = userEvent.setup();

    renderWithProviders(<EuAiActApplicabilityPanel />);

    expect(
      await screen.findByText(/Your AI roles suggest you may be a provider and a deployer/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use this" }));

    expect(screen.getByRole("checkbox", { name: /Provider/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Deployer/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Importer/ })).not.toBeChecked();
    // Nothing is saved until the person confirms.
    expect(euAiActApi.updateApplicability).not.toHaveBeenCalled();
    // And no suggestion is left to repeat once they're ticked.
    expect(screen.queryByRole("button", { name: "Use this" })).not.toBeInTheDocument();
  });

  it("makes no suggestion when the AI roles point to nothing", async () => {
    vi.mocked(euAiActApi.getApplicability).mockResolvedValue(makeApplicability());

    renderWithProviders(<EuAiActApplicabilityPanel />);

    await screen.findByLabelText("Yes, we're in scope");
    expect(screen.queryByText(/Your AI roles suggest/)).not.toBeInTheDocument();
  });
});

describe("EuAiActArticleTable", () => {
  it("shows each article's answer and why", async () => {
    vi.mocked(euAiActApi.listArticles).mockResolvedValue([makeArticle()]);

    renderWithProviders(<EuAiActArticleTable />);

    expect(await screen.findByText("not applicable")).toBeInTheDocument();
    expect(
      screen.getByText("Applies to providers; your organization isn't recorded as one."),
    ).toBeInTheDocument();
  });

  it("only saves an override once it has a justification", async () => {
    vi.mocked(euAiActApi.listArticles).mockResolvedValue([makeArticle()]);
    vi.mocked(euAiActApi.setOverride).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders(<EuAiActArticleTable />);

    await user.selectOptions(await screen.findByLabelText("Override for Art.16"), "applicable");
    const save = screen.getByRole("button", { name: "Save Override" });
    expect(save).toBeDisabled();

    await user.type(
      screen.getByLabelText("Override justification for Art.16"),
      "We took on provider duties.",
    );
    await user.click(save);

    expect(euAiActApi.setOverride).toHaveBeenCalledWith(
      16,
      "applicable",
      "We took on provider duties.",
    );
  });

  it("returns an overridden article to automatic straight away", async () => {
    vi.mocked(euAiActApi.listArticles).mockResolvedValue([
      makeArticle({
        override_applicability: "applicable",
        override_justification: "Contractual duty.",
        applicable: true,
      }),
    ]);
    vi.mocked(euAiActApi.clearOverride).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders(<EuAiActArticleTable />);

    await user.selectOptions(await screen.findByLabelText("Override for Art.16"), "automatic");

    expect(euAiActApi.clearOverride).toHaveBeenCalledWith(16);
  });
});
