import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useAISystemInventoryRows } from "../../ai-system-inventory/hooks";
import { useUserDirectory } from "../../users/hooks";
import { concernsApi } from "../api";
import { ConcernDetail } from "../components/ConcernDetail";
import { ConcernList } from "../components/ConcernList";
import { ConcernSettingsPanel } from "../components/ConcernSettingsPanel";
import { LogConcernForm } from "../components/LogConcernForm";
import { makeConcern } from "./fixtures";

vi.mock("../api");
vi.mock("../../ai-system-inventory/hooks");
vi.mock("../../users/hooks");
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: ({ entityType, entityId }: { entityType: string; entityId: number }) => (
    <p>{`Tags for ${entityType} ${entityId}`}</p>
  ),
}));

function renderWithProviders(ui: React.ReactNode) {
  vi.mocked(useAISystemInventoryRows).mockReturnValue({
    data: { rows: [{ id: 7, data: { name: "Resume Screener" } }] },
  } as never);
  vi.mocked(useUserDirectory).mockReturnValue({
    data: [{ id: 3, name: "Hana Handler", governance_roles: [] }],
  } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ConcernList", () => {
  const concerns = [
    makeConcern({ id: 1, description: "Brand new", status: "received" }),
    makeConcern({ id: 2, description: "Overdue one", awaiting_triage: true }),
    makeConcern({ id: 3, description: "Being looked at", status: "under_review" }),
    makeConcern({ id: 4, description: "All done", status: "resolved", outcome: "substantiated" }),
    makeConcern({
      id: 5,
      description: "Anon phone call",
      status: "not_actioned",
      channel: "phone",
      is_anonymous: true,
    }),
  ];

  it("shows the open ones by default and flags any not acknowledged in time", async () => {
    vi.mocked(concernsApi.list).mockResolvedValue(concerns);

    renderWithProviders(<ConcernList />);

    const rows = await screen.findAllByRole("row");
    const byText = (text: string) => rows.find((row) => row.textContent?.includes(text));
    expect(byText("Brand new")).toBeDefined();
    expect(byText("Being looked at")).toBeDefined();
    expect(byText("All done")).toBeUndefined();
    expect(byText("Anon phone call")).toBeUndefined();
    expect(byText("Overdue one")).toHaveClass("row-flagged");
    expect(byText("Overdue one")).toHaveTextContent("Not acknowledged");
    expect(byText("Brand new")).not.toHaveClass("row-flagged");
  });

  it("filters by status, and shows how each came in", async () => {
    vi.mocked(concernsApi.list).mockResolvedValue(concerns);
    const user = userEvent.setup();
    renderWithProviders(<ConcernList />);

    await user.selectOptions(await screen.findByLabelText("Show"), "not_actioned");

    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toHaveTextContent("Anon phone call");
    expect(rows[1]).toHaveTextContent("Phone call · anonymous");

    await user.selectOptions(screen.getByLabelText("Show"), "all");
    expect(screen.getAllByRole("row")).toHaveLength(6);
  });

  it("only shows the acknowledge-by date while a concern is still new", async () => {
    vi.mocked(concernsApi.list).mockResolvedValue([
      makeConcern({ id: 1, description: "New", status: "received", acknowledge_by: "2026-06-08" }),
      makeConcern({ id: 3, description: "Looked at", status: "under_review", acknowledge_by: "2026-06-08" }),
    ]);

    renderWithProviders(<ConcernList />);

    const rows = await screen.findAllByRole("row");
    expect(rows.find((r) => r.textContent?.includes("New"))).toHaveTextContent("2026-06-08");
    expect(rows.find((r) => r.textContent?.includes("Looked at"))).not.toHaveTextContent("2026-06-08");
  });

  it("says when nothing matches", async () => {
    vi.mocked(concernsApi.list).mockResolvedValue([]);

    renderWithProviders(<ConcernList />);

    expect(await screen.findByText("No concerns here.")).toBeInTheDocument();
  });
});

describe("LogConcernForm", () => {
  it("records a concern raised by phone, with what the person agreed to share", async () => {
    vi.mocked(concernsApi.log).mockResolvedValue(makeConcern({ id: 9 }));
    const onLogged = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<LogConcernForm onLogged={onLogged} />);

    await user.selectOptions(screen.getByLabelText("How was it raised?"), "email");
    await user.selectOptions(screen.getByLabelText("What is it about?"), "safety_or_harm");
    await user.type(screen.getByLabelText("What was said"), "A manager emailed about unsafe advice");
    await user.selectOptions(screen.getByLabelText("AI system"), "7");
    await user.type(screen.getByLabelText("What they agreed to share"), "Priya from support");
    await user.click(screen.getByRole("button", { name: "Record Concern" }));

    expect(concernsApi.log).toHaveBeenCalledWith({
      channel: "email",
      category: "safety_or_harm",
      description: "A manager emailed about unsafe advice",
      received_on: null,
      ai_system_row_id: 7,
      system_note: null,
      anonymous: false,
      reporter_note: "Priya from support",
    });
    expect(onLogged).toHaveBeenCalledWith(9);
  });

  it("drops what the person agreed to share when they asked to stay anonymous", async () => {
    vi.mocked(concernsApi.log).mockResolvedValue(makeConcern());
    const user = userEvent.setup();
    renderWithProviders(<LogConcernForm />);

    await user.type(screen.getByLabelText("What was said"), "Something worrying");
    await user.type(screen.getByLabelText("What they agreed to share"), "Priya");
    await user.click(screen.getByRole("checkbox", { name: "They asked to stay anonymous" }));
    expect(screen.queryByLabelText("What they agreed to share")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Record Concern" }));

    expect(concernsApi.log).toHaveBeenCalledWith(
      expect.objectContaining({ anonymous: true, reporter_note: null }),
    );
  });

  it("needs something written down", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LogConcernForm />);

    await user.click(screen.getByRole("button", { name: "Record Concern" }));

    expect(await screen.findByText("Write down what was said")).toBeInTheDocument();
    expect(concernsApi.log).not.toHaveBeenCalled();
  });
});

describe("ConcernDetail", () => {
  it("says who raised a named concern, and that an anonymous one can't be traced", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern());
    const { unmount } = renderWithProviders(<ConcernDetail concernId={1} />);
    expect(await screen.findByText("Raised by Elena Employee.")).toBeInTheDocument();
    unmount();

    vi.mocked(concernsApi.get).mockResolvedValue(
      makeConcern({ is_anonymous: true, reporter_id: null, reporter_name: null }),
    );
    renderWithProviders(<ConcernDetail concernId={1} />);
    expect(
      await screen.findByText(/Raised anonymously\. Nothing that identifies who raised it is stored\./),
    ).toBeInTheDocument();
  });

  it("offers the moves a new concern can make, and acknowledges it", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern());
    vi.mocked(concernsApi.setStatus).mockResolvedValue(makeConcern());
    const user = userEvent.setup();
    renderWithProviders(<ConcernDetail concernId={1} />);

    expect(await screen.findByRole("button", { name: "Acknowledge" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resolve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close without action" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reopen" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Acknowledge" }));
    // Acknowledging isn't a closure, so neither an outcome nor a note goes with it.
    expect(concernsApi.setStatus).toHaveBeenCalledWith(1, {
      action: "acknowledge",
      outcome: null,
      note: null,
    });
  });

  it("can't be acknowledged again once it's under review", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ status: "under_review" }));

    renderWithProviders(<ConcernDetail concernId={1} />);

    expect(await screen.findByRole("button", { name: "Resolve" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Acknowledge" })).not.toBeInTheDocument();
  });

  it("resolves with how it turned out and a note", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ status: "under_review" }));
    vi.mocked(concernsApi.setStatus).mockResolvedValue(makeConcern());
    const user = userEvent.setup();
    renderWithProviders(<ConcernDetail concernId={1} />);

    await user.selectOptions(await screen.findByLabelText("How it turned out"), "partly_substantiated");
    await user.type(screen.getByLabelText(/Note \(needed to close/), "Re-ranked; audit added");
    await user.click(screen.getByRole("button", { name: "Resolve" }));

    expect(concernsApi.setStatus).toHaveBeenCalledWith(1, {
      action: "resolve",
      outcome: "partly_substantiated",
      note: "Re-ranked; audit added",
    });
  });

  it("closes without action with the reason, and sends no outcome", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ status: "under_review" }));
    vi.mocked(concernsApi.setStatus).mockResolvedValue(makeConcern());
    const user = userEvent.setup();
    renderWithProviders(<ConcernDetail concernId={1} />);

    await user.type(await screen.findByLabelText(/Note \(needed to close/), "Outside our scope");
    await user.click(screen.getByRole("button", { name: "Close without action" }));

    expect(concernsApi.setStatus).toHaveBeenCalledWith(1, {
      action: "dismiss",
      outcome: null,
      note: "Outside our scope",
    });
  });

  it("only offers Reopen once closed, with no outcome or note fields", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(
      makeConcern({ status: "resolved", outcome: "substantiated", closed_on: "2026-06-20" }),
    );

    renderWithProviders(<ConcernDetail concernId={1} />);

    expect(await screen.findByRole("button", { name: "Reopen" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resolve" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("How it turned out")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Note \(needed to close/)).not.toBeInTheDocument();
  });

  it("saves the reply and the internal notes separately, each only when changed", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern());
    vi.mocked(concernsApi.update).mockResolvedValue(makeConcern());
    const user = userEvent.setup();
    renderWithProviders(<ConcernDetail concernId={1} />);

    await user.click(await screen.findByLabelText("Reply to the reporter"));
    await user.tab();
    expect(concernsApi.update).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Reply to the reporter"), "Thank you, we're on it.");
    await user.tab();
    expect(concernsApi.update).toHaveBeenLastCalledWith(1, {
      reply_to_reporter: "Thank you, we're on it.",
    });

    await user.type(screen.getByLabelText("Internal notes"), "Check the vendor");
    await user.tab();
    expect(concernsApi.update).toHaveBeenLastCalledWith(1, { internal_notes: "Check the vendor" });
  });

  it("raises an incident, and then links to it instead", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern());
    vi.mocked(concernsApi.raiseIncident).mockResolvedValue(makeConcern({ incident_id: 12 }));
    const user = userEvent.setup();
    const { unmount } = renderWithProviders(<ConcernDetail concernId={1} />);

    await user.click(await screen.findByRole("button", { name: "Raise as an Incident" }));
    expect(concernsApi.raiseIncident).toHaveBeenCalledWith(1);
    unmount();

    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ incident_id: 12 }));
    renderWithProviders(<ConcernDetail concernId={1} />);
    expect(await screen.findByRole("link", { name: "#12" })).toHaveAttribute("href", "/incidents/12");
    expect(screen.queryByRole("button", { name: "Raise as an Incident" })).not.toBeInTheDocument();
  });

  it("raises a corrective action for someone by a date, and lists what's been raised", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern());
    vi.mocked(concernsApi.listCorrectiveActions).mockResolvedValue([
      { id: 4, title: "Audit the ranking", status: "open" } as never,
    ]);
    vi.mocked(concernsApi.raiseCorrectiveAction).mockResolvedValue({} as never);
    const user = userEvent.setup();
    renderWithProviders(<ConcernDetail concernId={1} />);

    expect(await screen.findByRole("link", { name: "Audit the ranking" })).toHaveAttribute(
      "href",
      "/corrective-actions/4",
    );
    const raise = screen.getByRole("button", { name: "Raise Corrective Action" });
    expect(raise).toBeDisabled();
    await user.type(screen.getByLabelText("Corrective action"), "Retrain on a balanced sample");
    await user.selectOptions(screen.getByLabelText("Assigned to"), "3");
    await user.clear(screen.getByLabelText("Due"));
    await user.type(screen.getByLabelText("Due"), "2026-09-30");
    await user.click(raise);

    expect(concernsApi.raiseCorrectiveAction).toHaveBeenCalledWith(1, {
      title: "Retrain on a balanced sample",
      action_description: null,
      assignee_id: 3,
      due_date: "2026-09-30",
    });
  });

  it("links the AI system it is about, or shows what the reporter said", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ ai_system_row_id: 7 }));
    const { unmount } = renderWithProviders(<ConcernDetail concernId={1} />);
    expect(await screen.findByRole("link", { name: "Resume Screener" })).toHaveAttribute(
      "href",
      "/ai-systems/7",
    );
    unmount();

    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ system_note: "The HR portal" }));
    renderWithProviders(<ConcernDetail concernId={1} />);
    expect(await screen.findByText(/The HR portal/)).toBeInTheDocument();
  });

  it("flags one that hasn't been acknowledged in time", async () => {
    vi.mocked(concernsApi.get).mockResolvedValue(makeConcern({ awaiting_triage: true }));

    renderWithProviders(<ConcernDetail concernId={1} />);

    expect(await screen.findByText("Not acknowledged")).toBeInTheDocument();
    expect(screen.getByText(/acknowledge by 2026-06-08/)).toBeInTheDocument();
  });
});

describe("ConcernSettingsPanel", () => {
  const settings = {
    id: 1,
    process_description: "Tell us here.",
    acknowledge_within_days: 7,
    framework_tags: [],
  };

  it("saves what staff are told, on leaving the field and only when changed", async () => {
    vi.mocked(concernsApi.settings).mockResolvedValue(settings);
    vi.mocked(concernsApi.updateSettings).mockResolvedValue(settings);
    const user = userEvent.setup();
    renderWithProviders(<ConcernSettingsPanel />);

    await user.click(await screen.findByLabelText("What staff are told about reporting"));
    await user.tab();
    expect(concernsApi.updateSettings).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("What staff are told about reporting"), " Or call us.");
    await user.tab();
    expect(concernsApi.updateSettings).toHaveBeenCalledWith({
      process_description: "Tell us here. Or call us.",
    });
  });

  it("changes the acknowledgement window only to a sensible number of days", async () => {
    vi.mocked(concernsApi.settings).mockResolvedValue(settings);
    vi.mocked(concernsApi.updateSettings).mockResolvedValue(settings);
    const user = userEvent.setup();
    renderWithProviders(<ConcernSettingsPanel />);

    const days = await screen.findByLabelText("Acknowledge within (days)");
    const save = screen.getByRole("button", { name: "Save" });
    expect(save).toBeDisabled();

    await user.clear(days);
    await user.type(days, "0");
    expect(save).toBeDisabled();
    expect(screen.getByText(/whole number of days from 1 to 90/)).toBeInTheDocument();
    await user.clear(days);
    await user.type(days, "91");
    expect(save).toBeDisabled();

    await user.clear(days);
    await user.type(days, "3");
    expect(save).toBeEnabled();
    await user.click(save);
    expect(concernsApi.updateSettings).toHaveBeenCalledWith({ acknowledge_within_days: 3 });
  });

  it("lets the process be tagged to the clauses it evidences", async () => {
    vi.mocked(concernsApi.settings).mockResolvedValue(settings);

    renderWithProviders(<ConcernSettingsPanel />);

    expect(await screen.findByText("Tags for ConcernSettings 1")).toBeInTheDocument();
  });
});
