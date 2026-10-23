import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useCurrentUser } from "../../auth/hooks";
import { type AiSpendReport, aiAssistApi } from "../api";
import { AiSpendPanel } from "../components/AiSpendPanel";

vi.mock("../../auth/hooks");

const REPORT: AiSpendReport = {
  days: 30,
  calls: 12,
  prompt_tokens: 24000,
  completion_tokens: 3000,
  cache_read_tokens: 6000,
  cache_write_tokens: 500,
  cache_hit_rate: 0.25,
  by_feature: [
    {
      feature: "policy_draft",
      calls: 2,
      prompt_tokens: 12000,
      completion_tokens: 1800,
      average_prompt_tokens: 6000,
      average_completion_tokens: 900,
      cache_read_tokens: 0,
      cache_write_tokens: 0,
      cache_hit_rate: 0,
    },
    {
      feature: "assistant",
      calls: 10,
      prompt_tokens: 12000,
      completion_tokens: 1200,
      average_prompt_tokens: 1200,
      average_completion_tokens: 120,
      cache_read_tokens: 6000,
      cache_write_tokens: 500,
      cache_hit_rate: 0.5,
    },
  ],
  by_day: [],
};

function renderPanel() {
  render(
    <QueryClientProvider client={createTestQueryClient()}>
      <AiSpendPanel />
    </QueryClientProvider>,
  );
}

describe("AiSpendPanel", () => {
  beforeEach(() => {
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { role: "admin" },
    } as never);
    vi.spyOn(aiAssistApi, "spend").mockResolvedValue(REPORT);
  });

  it("totals the calls and tokens, then breaks them down by kind of call", async () => {
    renderPanel();

    await screen.findByText("Tokens sent");
    const tiles = Array.from(
      document.querySelectorAll(".usage-totals > div"),
    ).map((tile) => tile.textContent);
    expect(tiles).toEqual([
      "Calls12",
      "Tokens sent24,000",
      "Tokens written3,000",
      "Sent from a cache25%",
    ]);
    const rows = screen.getAllByRole("row").map((row) => row.textContent);
    // Costliest first, with its average sent and written, its total and its cache share.
    expect(rows[1]).toBe("Policy drafts26,00090013,8000%");
    expect(rows[2]).toBe("Assistant answers101,20012013,20050%");
  });

  it("names each kind of call plainly and shows its cache share", async () => {
    renderPanel();

    const row = (await screen.findByText("Assistant answers")).closest(
      "tr",
    ) as HTMLElement;
    expect(within(row).getByText("1,200")).toBeInTheDocument();
    expect(within(row).getByText("50%")).toBeInTheDocument();
  });

  it("reloads for another period", async () => {
    const user = userEvent.setup();
    renderPanel();

    await user.selectOptions(await screen.findByLabelText("Period"), "7");

    expect(aiAssistApi.spend).toHaveBeenCalledWith(30);
    expect(aiAssistApi.spend).toHaveBeenCalledWith(7);
  });

  it("says so when nothing has been spent", async () => {
    vi.spyOn(aiAssistApi, "spend").mockResolvedValue({
      ...REPORT,
      calls: 0,
      by_feature: [],
    });

    renderPanel();

    expect(
      await screen.findByText("No AI calls in this period."),
    ).toBeInTheDocument();
  });

  it("is not shown, and asks for nothing, to anyone but an administrator", () => {
    vi.mocked(useCurrentUser).mockReturnValue({
      data: { role: "viewer" },
    } as never);

    renderPanel();

    expect(
      screen.queryByText("Where the AI tokens go"),
    ).not.toBeInTheDocument();
    expect(aiAssistApi.spend).not.toHaveBeenCalled();
  });
});
