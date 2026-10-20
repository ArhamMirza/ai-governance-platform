import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAiAssistStatus } from "../../ai-assist/hooks";
import { organizationContextDraftApi } from "../aiDraft";
import { OrganizationContextDraftPanel } from "../components/OrganizationContextDraftPanel";
import type { OrganizationContext } from "../types";

vi.mock("../../ai-assist/hooks");

const CONTEXT = {} as OrganizationContext;

const SOURCES = [
  {
    key: "ai_systems",
    label: "AI systems in the inventory",
    count: 3,
    href: "/ai-systems",
    empty_note: "It cannot say what the organization uses AI for.",
  },
  {
    key: "policies",
    label: "Policies",
    count: 0,
    href: "/policies",
    empty_note: "It cannot say what rules the organization has set.",
  },
  {
    key: "ai_tools",
    label: "Approved AI tools",
    count: 0,
    href: "/ai-tools",
    empty_note:
      "It cannot say which AI tools staff are allowed to use, or from whom.",
  },
];

function renderPanel() {
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <OrganizationContextDraftPanel context={CONTEXT} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrganizationContextDraftPanel", () => {
  beforeEach(() => {
    vi.mocked(useAiAssistStatus).mockReturnValue({
      data: { available: true },
    } as never);
    vi.spyOn(organizationContextDraftApi, "latest").mockResolvedValue(null);
    vi.spyOn(organizationContextDraftApi, "readiness").mockResolvedValue(
      SOURCES,
    );
  });

  it("shows what the draft will read, and what is still empty", async () => {
    renderPanel();

    const list = await screen.findByRole("list");
    expect(
      within(list).getByText(/AI systems in the inventory/),
    ).toHaveTextContent("3");
    const policies = within(list).getByText(/Policies/);
    expect(policies).toHaveTextContent("none yet.");
    expect(policies).toHaveTextContent(
      "It cannot say what rules the organization has set.",
    );
  });

  it("links each empty kind to where it is filled in", async () => {
    renderPanel();

    await screen.findByRole("list");
    const links = screen.getAllByRole("link", { name: "Add some" });
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/policies",
      "/ai-tools",
    ]);
  });

  it("tells people to fill them in first, and that guidance cannot add facts", async () => {
    renderPanel();

    expect(
      await screen.findByText(/Fill these in first for a better draft/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/can’t add facts|can't add facts/),
    ).toBeInTheDocument();
  });

  it("drops the nudge when everything has something in it", async () => {
    vi.spyOn(organizationContextDraftApi, "readiness").mockResolvedValue(
      SOURCES.map((source) => ({ ...source, count: 2 })),
    );
    renderPanel();

    await screen.findByRole("list");
    expect(screen.queryByText(/Fill these in first/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Add some" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/The draft only states what these records say/),
    ).toBeInTheDocument();
  });

  it("shows nothing at all when no AI provider is set up", () => {
    vi.mocked(useAiAssistStatus).mockReturnValue({
      data: { available: false },
    } as never);

    renderPanel();

    expect(
      screen.queryByText("What the draft will read"),
    ).not.toBeInTheDocument();
  });
});
