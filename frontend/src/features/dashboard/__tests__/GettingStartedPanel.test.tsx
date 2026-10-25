import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useCurrentUser } from "../../auth/hooks";
import { dashboardApi } from "../api";
import { GettingStartedPanel } from "../components/GettingStartedPanel";
import type { GettingStarted } from "../types";

vi.mock("../../auth/hooks");

function make(overrides: Partial<GettingStarted> = {}): GettingStarted {
  return {
    steps: [
      {
        key: "organization",
        title: "Describe your organization",
        why: "Start here.",
        href: "/organization-context",
        done: true,
        optional: false,
      },
      {
        key: "roles",
        title: "Assign the Chief AI Governance Officer",
        why: "They approve policies and AI tools.",
        href: "/governance",
        done: false,
        optional: false,
      },
      {
        key: "assistant",
        title: "Turn on AI assistance",
        why: "Optional drafting and search.",
        href: "/settings",
        done: false,
        optional: true,
      },
    ],
    done_count: 1,
    total: 3,
    complete: false,
    next_key: "roles",
    ...overrides,
  };
}

function renderPanel() {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>
        <GettingStartedPanel />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("GettingStartedPanel", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { role: "admin" },
    } as never);
    vi.spyOn(dashboardApi, "getGettingStarted").mockResolvedValue(make());
  });

  it("lists the steps in order, with how many are done", async () => {
    renderPanel();

    expect(await screen.findByText("1 of 3 done")).toBeInTheDocument();
    const steps = screen.getAllByRole("listitem");
    expect(steps).toHaveLength(3);
    expect(
      within(steps[0]).getByRole("link", {
        name: "Describe your organization",
      }),
    ).toHaveAttribute("href", "/organization-context");
    expect(
      screen.getByRole("progressbar", { name: "Setup progress" }),
    ).toHaveAttribute("aria-valuenow", "1");
  });

  it("says which are done and which are to do, in words as well as marks", async () => {
    renderPanel();

    const steps = await screen.findAllByRole("listitem");
    expect(steps[0]).toHaveTextContent("Done: Describe your organization");
    expect(steps[1]).toHaveTextContent(
      "To do: Assign the Chief AI Governance Officer",
    );
  });

  it("points at the next step and explains it, but not the finished one", async () => {
    renderPanel();

    const steps = await screen.findAllByRole("listitem");
    expect(steps[1]).toHaveTextContent("Start here");
    expect(steps[1]).toHaveTextContent("They approve policies and AI tools.");
    expect(steps[0]).not.toHaveTextContent("Start here.");
    expect(steps[0]).not.toHaveTextContent("Start here");
    expect(steps[2]).toHaveTextContent("Optional");
  });

  it("can be hidden for now, remembered, and brought back", async () => {
    const user = userEvent.setup();
    const { unmount } = renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Hide for now" }),
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(screen.getByText(/1 of 3 done/)).toBeInTheDocument();
    unmount();

    renderPanel();
    await user.click(
      await screen.findByRole("button", { name: "Show getting started" }),
    );
    expect(await screen.findByRole("list")).toBeInTheDocument();
  });

  it("is gone once every required step is done", async () => {
    vi.spyOn(dashboardApi, "getGettingStarted").mockResolvedValue(
      make({ complete: true, done_count: 2, next_key: null }),
    );

    const { container } = renderPanel();

    await vi.waitFor(() =>
      expect(dashboardApi.getGettingStarted).toHaveBeenCalled(),
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("is not shown, and asks for nothing, to someone who cannot make the records", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { role: "viewer" },
    } as never);

    const { container } = renderPanel();

    expect(container).toBeEmptyDOMElement();
    expect(dashboardApi.getGettingStarted).not.toHaveBeenCalled();
  });

  it("still works where the browser will not let it remember", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const user = userEvent.setup();
    renderPanel();

    await user.click(
      await screen.findByRole("button", { name: "Hide for now" }),
    );

    expect(
      screen.getByRole("button", { name: "Show getting started" }),
    ).toBeInTheDocument();
    vi.restoreAllMocks();
  });
});
