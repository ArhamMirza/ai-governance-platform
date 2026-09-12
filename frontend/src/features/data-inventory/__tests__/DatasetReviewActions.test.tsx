import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { useCurrentUser } from "../../auth/hooks";
import { useCanApprove } from "../../audit-log/useCanApprove";
import type { SheetRow } from "../../sheets/types";
import { DatasetReviewActions } from "../components/DatasetReviewActions";
import { useApproveDataset, useSubmitDatasetForApproval } from "../hooks";

vi.mock("../hooks");
vi.mock("../../auth/hooks");
vi.mock("../../audit-log/useCanApprove");

function makeRow(data: Record<string, unknown>): SheetRow {
  return {
    id: 5,
    sheet_id: 1,
    row_index: 1,
    data: { dataset_name: "Resume corpus", ...data },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function mockHooks({
  me = { id: 9, role: "contributor" },
  canApprove = { canApprove: true, reason: null } as { canApprove: boolean; reason: string | null },
  submit = vi.fn(),
  approve = vi.fn(),
} = {}) {
  vi.mocked(useCurrentUser).mockReturnValue({ data: me } as never);
  vi.mocked(useCanApprove).mockReturnValue(canApprove as never);
  vi.mocked(useSubmitDatasetForApproval).mockReturnValue({
    mutateAsync: submit,
    isPending: false,
  } as never);
  vi.mocked(useApproveDataset).mockReturnValue({
    mutateAsync: approve,
    isPending: false,
  } as never);
  return { submit, approve };
}

describe("DatasetReviewActions", () => {
  it("lets the assigned data owner submit a draft", async () => {
    const { submit } = mockHooks();
    const user = userEvent.setup();

    render(<DatasetReviewActions row={makeRow({ approval_status: "draft", data_owner: "9" })} />);
    await user.click(screen.getByRole("button", { name: "Submit for approval" }));

    await waitFor(() => expect(submit).toHaveBeenCalledWith(5));
  });

  it("does not offer submission to someone who isn't the data owner", () => {
    mockHooks();

    render(<DatasetReviewActions row={makeRow({ approval_status: "draft", data_owner: "42" })} />);

    expect(
      screen.queryByRole("button", { name: "Submit for approval" }),
    ).not.toBeInTheDocument();
  });

  it("lets an admin submit someone else's draft", () => {
    mockHooks({ me: { id: 9, role: "admin" } });

    render(<DatasetReviewActions row={makeRow({ approval_status: "draft", data_owner: "42" })} />);

    expect(screen.getByRole("button", { name: "Submit for approval" })).toBeInTheDocument();
  });

  it("offers submission on a dataset nobody owns yet", () => {
    mockHooks();

    render(<DatasetReviewActions row={makeRow({ approval_status: "draft" })} />);

    expect(screen.getByRole("button", { name: "Submit for approval" })).toBeInTheDocument();
  });

  it("offers approval on a submitted dataset when the user may approve", async () => {
    const { approve } = mockHooks();
    const user = userEvent.setup();

    render(<DatasetReviewActions row={makeRow({ approval_status: "pending_approval" })} />);
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(approve).toHaveBeenCalledWith(5));
  });

  it("explains why instead of offering approval when the user may not approve", () => {
    mockHooks({
      canApprove: {
        canApprove: false,
        reason: "Only the Chief AI Governance Officer can approve.",
      },
    });

    render(<DatasetReviewActions row={makeRow({ approval_status: "pending_approval" })} />);

    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Only the Chief AI Governance Officer can approve."),
    ).toBeInTheDocument();
  });

  it("offers nothing on an already approved dataset", () => {
    mockHooks();

    const { container } = render(
      <DatasetReviewActions row={makeRow({ approval_status: "approved", data_owner: "9" })} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
