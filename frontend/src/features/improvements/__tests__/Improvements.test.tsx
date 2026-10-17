import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useUserDirectory } from "../../users/hooks";
import { improvementsApi } from "../api";
import { ImprovementDetail } from "../components/ImprovementDetail";
import { ImprovementForm } from "../components/ImprovementForm";
import { ImprovementList } from "../components/ImprovementList";
import { ImprovementsAsOf } from "../components/ImprovementsAsOf";
import { SourceImprovements } from "../components/SourceImprovements";
import { makeImprovement } from "./fixtures";

vi.mock("../api");
vi.mock("../../users/hooks");
vi.mock("../../framework-tags/components/FrameworkTagPicker", () => ({
  FrameworkTagPicker: () => null,
}));
vi.mock("../../evidence/components/DocumentBrowser", () => ({ DocumentBrowser: () => null }));
vi.mock("../../audit-log/components/AuditLogViewer", () => ({ AuditLogViewer: () => null }));

function renderWithProviders(ui: React.ReactNode) {
  vi.mocked(useUserDirectory).mockReturnValue({
    data: [{ id: 3, name: "Olu Owner", governance_roles: [] }],
  } as never);
  return render(
    <QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImprovementList", () => {
  const improvements = [
    makeImprovement({ id: 1, title: "Proposed one" }),
    makeImprovement({
      id: 2,
      title: "Late one",
      status: "accepted",
      standing: { state: "accepted", overdue: true },
    }),
    makeImprovement({
      id: 3,
      title: "Done one",
      status: "implemented",
      source: "internal_audit",
      standing: { state: "implemented", overdue: false },
    }),
    makeImprovement({
      id: 4,
      title: "Declined one",
      status: "declined",
      standing: { state: "declined", overdue: false },
    }),
  ];

  it("shows the open ones by default and flags only the overdue", async () => {
    vi.mocked(improvementsApi.list).mockResolvedValue(improvements);

    renderWithProviders(<ImprovementList />);

    const rows = await screen.findAllByRole("row");
    const row = (text: string) => rows.find((r) => r.textContent?.includes(text));
    expect(rows).toHaveLength(3);
    expect(row("Late one")).toHaveClass("row-flagged");
    expect(row("Late one")).toHaveTextContent("Overdue");
    expect(row("Proposed one")).not.toHaveClass("row-flagged");
    expect(row("Done one")).toBeUndefined();
  });

  it("filters by status and says where each came from", async () => {
    vi.mocked(improvementsApi.list).mockResolvedValue(improvements);
    const user = userEvent.setup();
    renderWithProviders(<ImprovementList />);

    await user.selectOptions(await screen.findByLabelText("Show"), "implemented");

    const rows = screen.getAllByRole("row");
    expect(rows).toHaveLength(2);
    expect(rows[1]).toHaveTextContent("Done one");
    expect(rows[1]).toHaveTextContent("An internal audit");

    await user.selectOptions(screen.getByLabelText("Show"), "all");
    expect(screen.getAllByRole("row")).toHaveLength(5);
  });

  it("says when nothing matches", async () => {
    vi.mocked(improvementsApi.list).mockResolvedValue([]);

    renderWithProviders(<ImprovementList />);

    expect(await screen.findByText("No improvements here.")).toBeInTheDocument();
  });
});

describe("ImprovementForm", () => {
  it("records an improvement with where it came from, who owns it and by when", async () => {
    vi.mocked(improvementsApi.create).mockResolvedValue(makeImprovement({ id: 9 }));
    const onCreated = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<ImprovementForm onCreated={onCreated} />);

    await user.selectOptions(screen.getByLabelText("Where it came from"), "stakeholder_feedback");
    await user.type(screen.getByLabelText("Improvement"), "Publish model cards");
    await user.type(screen.getByLabelText("Expected benefit"), "  Clearer limits  ");
    await user.selectOptions(screen.getByLabelText("Owner"), "3");
    await user.clear(screen.getByLabelText("Raised on"));
    await user.type(screen.getByLabelText("Raised on"), "2026-06-01");
    await user.type(screen.getByLabelText("Target date"), "2026-09-30");
    await user.click(screen.getByRole("button", { name: "Add Improvement" }));

    expect(improvementsApi.create).toHaveBeenCalledWith({
      title: "Publish model cards",
      description: null,
      expected_benefit: "Clearer limits",
      source: "stakeholder_feedback",
      source_type: null,
      source_id: null,
      owner_id: 3,
      raised_on: "2026-06-01",
      target_date: "2026-09-30",
    });
    expect(onCreated).toHaveBeenCalledWith(9);
  });

  it("when raised from a record, links it and starts from its text", async () => {
    vi.mocked(improvementsApi.create).mockResolvedValue(makeImprovement({ id: 9 }));
    const user = userEvent.setup();
    renderWithProviders(
      <ImprovementForm
        from={{
          sourceType: "AuditFinding",
          sourceId: 4,
          label: "a finding in Q1 Audit",
          description: "Risk owners are named by team.",
        }}
      />,
    );

    expect(screen.getByText("Raised from a finding in Q1 Audit.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Where it came from")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Description")).toHaveValue("Risk owners are named by team.");
    await user.type(screen.getByLabelText("Improvement"), "Name owners");
    await user.type(screen.getByLabelText("Target date"), "2099-01-01");
    await user.click(screen.getByRole("button", { name: "Add Improvement" }));

    expect(improvementsApi.create).toHaveBeenCalledWith(
      expect.objectContaining({
        source_type: "AuditFinding",
        source_id: 4,
        description: "Risk owners are named by team.",
      }),
    );
  });

  it("refuses a target before it was raised", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ImprovementForm />);

    await user.type(screen.getByLabelText("Improvement"), "Backwards");
    await user.clear(screen.getByLabelText("Raised on"));
    await user.type(screen.getByLabelText("Raised on"), "2026-06-10");
    await user.type(screen.getByLabelText("Target date"), "2026-06-01");
    await user.click(screen.getByRole("button", { name: "Add Improvement" }));

    expect(
      await screen.findByText("The target date can't be before it was raised"),
    ).toBeInTheDocument();
    expect(improvementsApi.create).not.toHaveBeenCalled();
  });
});

describe("ImprovementDetail", () => {
  it("accepts a proposal, with no note", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(makeImprovement());
    vi.mocked(improvementsApi.setStatus).mockResolvedValue(makeImprovement());
    const user = userEvent.setup();
    renderWithProviders(<ImprovementDetail improvementId={1} />);

    expect(await screen.findByRole("button", { name: "Decline" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Mark Implemented" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Accept" }));

    expect(improvementsApi.setStatus).toHaveBeenCalledWith(1, { action: "accept", note: null });
  });

  it("needs the outcome to mark it implemented, and sends it", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({ status: "accepted", standing: { state: "accepted", overdue: false } }),
    );
    vi.mocked(improvementsApi.setStatus).mockResolvedValue(makeImprovement());
    const user = userEvent.setup();
    renderWithProviders(<ImprovementDetail improvementId={1} />);

    const implement = await screen.findByRole("button", { name: "Mark Implemented" });
    expect(implement).toBeDisabled();
    await user.type(screen.getByLabelText("What changed, and did it work?"), "   ");
    expect(implement).toBeDisabled();
    await user.type(screen.getByLabelText("What changed, and did it work?"), "Owners named");
    // A reason typed for declining doesn't go with implementing.
    await user.type(screen.getByLabelText("Why it isn't going ahead"), "Not this");
    await user.click(implement);

    expect(improvementsApi.setStatus).toHaveBeenCalledWith(1, {
      action: "implement",
      note: "Owners named",
    });
  });

  it("only offers Reopen once closed, and shows what came of it", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({
        status: "implemented",
        outcome: "Owners named on every risk item",
        closed_on: "2026-07-01",
        standing: { state: "implemented", overdue: false },
      }),
    );

    renderWithProviders(<ImprovementDetail improvementId={1} />);

    expect(await screen.findByRole("button", { name: "Reopen" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
    expect(screen.getByText("Owners named on every risk item")).toBeInTheDocument();
    expect(screen.getByText(/closed 2026-07-01/)).toBeInTheDocument();
  });

  it("carries an accepted improvement out as a change, then links to it", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({ status: "accepted", standing: { state: "accepted", overdue: false } }),
    );
    vi.mocked(improvementsApi.carryOutAsChange).mockResolvedValue(makeImprovement());
    const user = userEvent.setup();
    const { unmount } = renderWithProviders(<ImprovementDetail improvementId={1} />);

    await user.click(await screen.findByRole("button", { name: "Carry Out as a Change" }));
    expect(improvementsApi.carryOutAsChange).toHaveBeenCalledWith(1);
    unmount();

    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({
        status: "accepted",
        change_id: 12,
        standing: { state: "accepted", overdue: false },
      }),
    );
    renderWithProviders(<ImprovementDetail improvementId={1} />);
    expect(await screen.findByRole("link", { name: "a planned change" })).toHaveAttribute(
      "href",
      "/changes/12",
    );
    expect(screen.queryByRole("button", { name: "Carry Out as a Change" })).not.toBeInTheDocument();
  });

  it("can't be carried out as a change before it's accepted", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(makeImprovement());

    renderWithProviders(<ImprovementDetail improvementId={1} />);

    expect(await screen.findByText("Accept it first to plan it as a change.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Carry Out as a Change" })).not.toBeInTheDocument();
  });

  it.each([
    [
      { source_type: "AIIncident", source_id: 5, source_label: "Chatbot gave unsafe advice" },
      "/incidents/5",
    ],
    [{ source_type: "Concern", source_id: 2, source_label: "Concern #2" }, "/concerns/2"],
  ] as const)("links back to where it came from", async (source, href) => {
    vi.mocked(improvementsApi.get).mockResolvedValue(makeImprovement({ ...source }));

    renderWithProviders(<ImprovementDetail improvementId={1} />);

    expect(await screen.findByRole("link", { name: source.source_label })).toHaveAttribute(
      "href",
      href,
    );
  });

  it("names a source that has since gone, and one that never had a record", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({ source_type: "AIIncident", source_id: 5, source_label: null }),
    );
    const { unmount } = renderWithProviders(<ImprovementDetail improvementId={1} />);
    expect(
      await screen.findByText("Came from a record that no longer exists."),
    ).toBeInTheDocument();
    unmount();

    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({ source: "stakeholder_feedback" }),
    );
    renderWithProviders(<ImprovementDetail improvementId={1} />);
    expect(
      await screen.findByText("Came from feedback from an interested party."),
    ).toBeInTheDocument();
  });

  it("saves an edited field only when it changed", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(makeImprovement());
    vi.mocked(improvementsApi.update).mockResolvedValue(makeImprovement());
    const user = userEvent.setup();
    renderWithProviders(<ImprovementDetail improvementId={1} />);

    await user.click(await screen.findByLabelText("Expected benefit"));
    await user.tab();
    expect(improvementsApi.update).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("Expected benefit"), "Fewer stalled treatments");
    await user.tab();
    expect(improvementsApi.update).toHaveBeenCalledWith(1, {
      expected_benefit: "Fewer stalled treatments",
    });
  });

  it("only lets a proposal be deleted", async () => {
    vi.mocked(improvementsApi.get).mockResolvedValue(
      makeImprovement({ status: "accepted", standing: { state: "accepted", overdue: false } }),
    );

    renderWithProviders(<ImprovementDetail improvementId={1} />);

    expect(await screen.findByText(/Decline it instead of deleting it/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Improvement" })).not.toBeInTheDocument();
  });
});

describe("ImprovementsAsOf", () => {
  it("shows each improvement as it stood on the meeting's date", async () => {
    vi.mocked(improvementsApi.standingAsOf).mockResolvedValue([
      {
        id: 1,
        title: "Model cards",
        source: "stakeholder_feedback",
        owner_id: null,
        target_date: "2026-08-01",
        standing: { state: "accepted", overdue: true },
      },
    ]);

    renderWithProviders(<ImprovementsAsOf asOf="2026-09-01" />);

    expect(await screen.findByRole("link", { name: "Model cards" })).toBeInTheDocument();
    expect(improvementsApi.standingAsOf).toHaveBeenCalledWith("2026-09-01");
    expect(screen.getByText("Overdue")).toBeInTheDocument();
    expect(screen.getByText("Feedback from an interested party")).toBeInTheDocument();
  });

  it("says when none had been raised by then", async () => {
    vi.mocked(improvementsApi.standingAsOf).mockResolvedValue([]);

    renderWithProviders(<ImprovementsAsOf asOf="2026-09-01" />);

    expect(
      await screen.findByText("No improvements had been raised by this date."),
    ).toBeInTheDocument();
  });
});

function ShowState() {
  const location = useLocation();
  return <pre data-testid="state">{JSON.stringify(location.state)}</pre>;
}

describe("SourceImprovements", () => {
  it("lists what was raised from a record and raises another, carrying the record", async () => {
    vi.mocked(improvementsApi.listForSource).mockResolvedValue([
      makeImprovement({ id: 7, title: "Name owners" }),
    ]);
    const user = userEvent.setup();
    const from = { sourceType: "Concern" as const, sourceId: 2, label: "concern #2" };
    render(
      <QueryClientProvider client={createTestQueryClient()}>
        <MemoryRouter initialEntries={["/concerns/2"]}>
          <Routes>
            <Route path="/concerns/2" element={<SourceImprovements from={from} />} />
            <Route path="/improvements" element={<ShowState />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("link", { name: "Name owners" })).toHaveAttribute(
      "href",
      "/improvements/7",
    );
    expect(improvementsApi.listForSource).toHaveBeenCalledWith("Concern", 2);
    await user.click(screen.getByRole("button", { name: "Raise Improvement" }));

    expect(JSON.parse(screen.getByTestId("state").textContent ?? "null")).toEqual(from);
  });
});
