import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { frameworkTagsApi } from "../../framework-tags/api";
import { managementReviewApi } from "../api";
import { ManagementReviewSettingsPanel } from "../components/ManagementReviewSettingsPanel";
import type { ManagementReviewSettings } from "../types";

vi.mock("../api");
vi.mock("../../framework-tags/api");

function renderWithProviders(ui: React.ReactNode) {
  const queryClient = createTestQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function makeSettings(overrides: Partial<ManagementReviewSettings> = {}): ManagementReviewSettings {
  return {
    interval_months: null,
    start_date: null,
    next_due_date: null,
    overdue: false,
    framework_tags: [],
    updated_at: null,
    ...overrides,
  };
}

describe("ManagementReviewSettingsPanel", () => {
  it("shows no-schedule copy when unconfigured", async () => {
    vi.mocked(managementReviewApi.getSettings).mockResolvedValue(makeSettings());
    vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);

    renderWithProviders(<ManagementReviewSettingsPanel />);

    expect(
      await screen.findByText("No schedule configured -- reviews are logged as they happen."),
    ).toBeInTheDocument();
  });

  it("reveals interval and start-date fields only once recurring is checked", async () => {
    vi.mocked(managementReviewApi.getSettings).mockResolvedValue(makeSettings());
    vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders(<ManagementReviewSettingsPanel />);
    await user.click(await screen.findByRole("button", { name: "Edit" }));

    expect(screen.queryByLabelText("Every how many months")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Recurring reviews"));

    expect(screen.getByLabelText("Every how many months")).toBeInTheDocument();
    expect(screen.getByLabelText("First review due")).toBeInTheDocument();
  });

  it("shows the overdue flag", async () => {
    vi.mocked(managementReviewApi.getSettings).mockResolvedValue(
      makeSettings({ interval_months: 12, next_due_date: "2020-01-01", overdue: true }),
    );
    vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);

    renderWithProviders(<ManagementReviewSettingsPanel />);

    expect(await screen.findByText("Overdue")).toBeInTheDocument();
  });

  it("saves a configured interval", async () => {
    vi.mocked(managementReviewApi.getSettings).mockResolvedValue(makeSettings());
    vi.mocked(managementReviewApi.updateSettings).mockResolvedValue(
      makeSettings({ interval_months: 12, start_date: "2026-01-01" }),
    );
    vi.mocked(frameworkTagsApi.get).mockResolvedValue([]);
    const user = userEvent.setup();

    renderWithProviders(<ManagementReviewSettingsPanel />);
    await user.click(await screen.findByRole("button", { name: "Edit" }));
    await user.click(screen.getByLabelText("Recurring reviews"));
    await user.type(screen.getByLabelText("Every how many months"), "12");
    await user.type(screen.getByLabelText("First review due"), "2026-01-01");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await vi.waitFor(() => {
      expect(managementReviewApi.updateSettings).toHaveBeenCalledWith({
        interval_months: 12,
        start_date: "2026-01-01",
      });
    });
  });
});
