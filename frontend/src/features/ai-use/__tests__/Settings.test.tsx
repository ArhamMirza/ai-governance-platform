import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import { createTestQueryClient } from "../../../test/testQueryClient";
import { aiUseApi, staffAiUseApi } from "../api";
import { AIToolsSubNav } from "../components/AIToolsSubNav";
import { CoveragePanel } from "../components/CoveragePanel";
import { AIUseSettingsPanel } from "../components/AIUseSettingsPanel";
import { StaffAIUseNotice } from "../components/StaffAIUseNotice";
import { UsagePanel } from "../components/UsagePanel";
import { makeCoverage, makeSettings, makeUsage } from "./fixtures";

vi.mock("../api");

function renderWithProviders(ui: React.ReactNode, path = "/") {
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AIUseSettingsPanel", () => {
  it("changes what the browser does on an unapproved site", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings());
    vi.mocked(aiUseApi.updateSettings).mockResolvedValue(makeSettings());
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    await user.selectOptions(await screen.findByLabelText("What the browser does"), "block");

    expect(aiUseApi.updateSettings).toHaveBeenCalledWith({ unapproved_site_action: "block" });
  });

  it("saves the staff notice on leaving the field, only when it changed", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings({ staff_notice: "We count visits." }));
    vi.mocked(aiUseApi.updateSettings).mockResolvedValue(makeSettings());
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    const notice = await screen.findByLabelText("Notice shown to employees");
    await user.click(notice);
    await user.tab();
    expect(aiUseApi.updateSettings).not.toHaveBeenCalled();

    await user.type(notice, " Never what you type.");
    await user.tab();
    expect(aiUseApi.updateSettings).toHaveBeenCalledWith({
      staff_notice: "We count visits. Never what you type.",
    });
  });

  it("clears the notice to nothing, not to blank text", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings({ staff_notice: "Old" }));
    vi.mocked(aiUseApi.updateSettings).mockResolvedValue(makeSettings());
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    const notice = await screen.findByLabelText("Notice shown to employees");
    await user.clear(notice);
    await user.type(notice, "   ");
    await user.tab();

    expect(aiUseApi.updateSettings).toHaveBeenCalledWith({ staff_notice: null });
  });

  it("only saves a sensible retention period", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings());
    vi.mocked(aiUseApi.updateSettings).mockResolvedValue(makeSettings());
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    const days = await screen.findByLabelText("Days");
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled(); // unchanged

    await user.clear(days);
    await user.type(days, "3");
    expect(save).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("from 7 to 730");
    await user.clear(days);
    await user.type(days, "731");
    expect(save).toBeDisabled();
    await user.clear(days);
    await user.type(days, "7.5");
    expect(save).toBeDisabled();

    await user.clear(days);
    await user.type(days, "30");
    expect(save).toBeEnabled();
    await user.click(save);
    expect(aiUseApi.updateSettings).toHaveBeenCalledWith({ retention_days: 30 });
  });

  it("says no key has been made, and shows the new one once", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings());
    vi.mocked(aiUseApi.rotateKey).mockResolvedValue({ key: "aigk_NEWKEYVALUE1234", hint: "1234" });
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    expect(await screen.findByText(/No key has been made/)).toBeInTheDocument();
    // No confirmation is asked for when there is nothing to replace.
    const confirm = vi.spyOn(window, "confirm");
    await user.click(screen.getByRole("button", { name: "Create Key" }));

    expect(await screen.findByText("aigk_NEWKEYVALUE1234")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("shown once and can't be shown again");
    expect(confirm).not.toHaveBeenCalled();
    confirm.mockRestore();
  });

  it("asks before replacing a key, because browsers using the old one stop reporting", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(
      makeSettings({
        enrollment_key_issued: true,
        enrollment_key_hint: "ab12",
        enrollment_key_created_on: "2026-05-01",
      }),
    );
    vi.mocked(aiUseApi.rotateKey).mockResolvedValue({ key: "aigk_REPLACEMENT", hint: "MENT" });
    const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    expect(await screen.findByText("A key ending ab12 was made on 2026-05-01.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Replace Key" }));
    expect(aiUseApi.rotateKey).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Replace Key" }));
    expect(await screen.findByText("aigk_REPLACEMENT")).toBeInTheDocument();
    expect(confirm).toHaveBeenCalledTimes(2);
    confirm.mockRestore();
  });

  it("copies the key to the clipboard", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings());
    vi.mocked(aiUseApi.rotateKey).mockResolvedValue({ key: "aigk_COPYME", hint: "OPYME" });
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    await user.click(await screen.findByRole("button", { name: "Create Key" }));
    await user.click(await screen.findByRole("button", { name: "Copy key" }));

    expect(await navigator.clipboard.readText()).toBe("aigk_COPYME");
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("says why a setting couldn't be saved", async () => {
    vi.mocked(aiUseApi.settings).mockResolvedValue(makeSettings());
    vi.mocked(aiUseApi.updateSettings).mockRejectedValue(
      new ApiError(400, JSON.stringify({ detail: "That setting needs a value." })),
    );
    const user = userEvent.setup();
    renderWithProviders(<AIUseSettingsPanel />);

    await user.selectOptions(await screen.findByLabelText("What the browser does"), "warn");

    expect(await screen.findByRole("alert")).toHaveTextContent("That setting needs a value.");
  });
});

describe("UsagePanel", () => {
  it("totals what happened, then breaks it down by site, rule, person and day", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage());
    renderWithProviders(<UsagePanel />);

    await screen.findByText("Visits to unapproved AI sites");
    const tiles = Array.from(document.querySelectorAll(".usage-totals > div")).map(
      (tile) => tile.textContent,
    );
    // Types with no events aren't listed as zeros.
    expect(tiles).toEqual([
      "Visits to unapproved AI sites14",
      "Sensitive data caught6",
      "Times someone went ahead past a warning3",
    ]);

    const rows = screen.getAllByRole("row").map((row) => row.textContent);
    expect(rows).toContainEqual(expect.stringContaining("Claude" + "claude.ai"));
    // A site that isn't in the catalogue falls back to its address.
    expect(rows).toContainEqual(expect.stringMatching(/^grok\.com.*5.*2.*0.*0$/));
    expect(rows).toContainEqual(expect.stringContaining("Payment card numbers65"));
    expect(rows).toContainEqual(expect.stringContaining("Elena Employeeelena@example.com963"));
    expect(rows).toContainEqual(expect.stringMatching(/^bob@example\.com500$/));
    expect(screen.getByLabelText("By day")).toHaveTextContent("2026-06-02");
    expect(screen.getByLabelText("By day")).toHaveTextContent("10 site visits, 6 caught");
    expect(screen.getByLabelText("By day")).toHaveTextContent("4 site visits, 0 caught");
  });

  it("scales each day's bar to the busiest day", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage());
    renderWithProviders(<UsagePanel />);

    await screen.findByLabelText("By day");
    const fills = Array.from(document.querySelectorAll<HTMLElement>(".usage-bar-fill"));

    expect(fills.map((fill) => fill.style.width)).toEqual(["25%", "100%"]);
  });

  it("reloads for another period", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage());
    const user = userEvent.setup();
    renderWithProviders(<UsagePanel />);

    await user.selectOptions(await screen.findByLabelText("Period"), "7");

    expect(aiUseApi.usage).toHaveBeenCalledWith(30);
    expect(aiUseApi.usage).toHaveBeenCalledWith(7);
  });

  it("shows a deleted rule by its number, and leaves out an empty rules table", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(
      makeUsage({ by_rule: [{ rule_id: 9, rule_name: null, matches: 2, blocked: 0 }] }),
    );
    const { unmount } = renderWithProviders(<UsagePanel />);
    expect(await screen.findByText("Deleted rule #9")).toBeInTheDocument();
    unmount();

    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage({ by_rule: [] }));
    renderWithProviders(<UsagePanel />);
    await screen.findByText("By person");
    expect(screen.queryByText("By rule")).not.toBeInTheDocument();
  });

  it("says when nothing has been reported", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage({ by_type: [] }));

    renderWithProviders(<UsagePanel />);

    expect(await screen.findByText(/Nothing reported in this period/)).toBeInTheDocument();
  });
});

describe("UsagePanel overrides", () => {
  it("leaves the override tile out when nobody went ahead past a warning", async () => {
    vi.mocked(aiUseApi.usage).mockResolvedValue(makeUsage({ overrides: 0 }));

    renderWithProviders(<UsagePanel />);

    await screen.findByText("Visits to unapproved AI sites");
    expect(screen.queryByText(/went ahead past a warning/)).not.toBeInTheDocument();
  });
});

describe("CoveragePanel", () => {
  it("says how many people have reported and lists those who haven't, worst first", async () => {
    vi.mocked(aiUseApi.coverage).mockResolvedValue(makeCoverage());

    renderWithProviders(<CoveragePanel />);

    expect(await screen.findByText(/1 of 3/)).toBeInTheDocument();
    expect(screen.getByText(/reported in\s+the last 7 days/)).toBeInTheDocument();
    const rows = screen.getAllByRole("row").map((row) => row.textContent);
    expect(rows).toContainEqual(expect.stringContaining("Nora Nevernora@example.comNever reportedNever"));
    expect(rows).toContainEqual(
      expect.stringContaining("Quentin Quietquentin@example.comGone quiet2026-05-01"),
    );
    // Someone who is reporting needs no row.
    expect(rows.join()).not.toContain("Elena");
  });

  it("explains browsers that match no account", async () => {
    vi.mocked(aiUseApi.coverage).mockResolvedValue(makeCoverage({ unmatched_reporters: 2 }));

    renderWithProviders(<CoveragePanel />);

    expect(await screen.findByText(/2 other browsers reported in under an address/)).toBeInTheDocument();
  });

  it("shows no table when everyone has reported", async () => {
    vi.mocked(aiUseApi.coverage).mockResolvedValue(
      makeCoverage({ active_people: 1, reporting: 1, people: [makeCoverage().people[2]] }),
    );

    renderWithProviders(<CoveragePanel />);

    expect(await screen.findByText(/1 of 1/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("says so when it can't load", async () => {
    vi.mocked(aiUseApi.coverage).mockRejectedValue(new ApiError(500, "nope"));

    renderWithProviders(<CoveragePanel />);

    expect(await screen.findByText("Failed to load coverage.")).toBeInTheDocument();
  });
});

describe("StaffAIUseNotice", () => {
  it.each([
    ["monitor", "Opening an AI website that hasn't been approved is counted."],
    ["warn", "Opening an AI website that hasn't been approved shows you a warning first."],
    ["block", "AI websites that haven't been approved are blocked."],
  ] as const)("tells staff what happens on an unapproved site (%s)", async (action, text) => {
    vi.mocked(staffAiUseApi.notice).mockResolvedValue({
      staff_notice: "We never read what you type.",
      unapproved_site_action: action,
    });

    renderWithProviders(<StaffAIUseNotice />);

    expect(await screen.findByText(text)).toBeInTheDocument();
    expect(screen.getByText("We never read what you type.")).toBeInTheDocument();
  });

  it("says plainly when nothing has been published", async () => {
    vi.mocked(staffAiUseApi.notice).mockResolvedValue({
      staff_notice: null,
      unapproved_site_action: "monitor",
    });

    renderWithProviders(<StaffAIUseNotice />);

    expect(await screen.findByText(/Nothing has been published about monitoring yet/)).toBeInTheDocument();
  });
});

describe("AIToolsSubNav", () => {
  it("links the sections and marks the one you are on", () => {
    renderWithProviders(<AIToolsSubNav />, "/ai-tools/rules");

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual([
      "/ai-tools",
      "/ai-tools/rules",
      "/ai-tools/usage",
      "/ai-tools/settings",
    ]);
    expect(screen.getByRole("link", { name: "Data rules" })).toHaveClass("active");
    expect(screen.getByRole("link", { name: "Tools and requests" })).not.toHaveClass("active");
  });
});
