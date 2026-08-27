import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
import type { SheetRow } from "../../sheets/types";
import {
  useCreateFolder,
  useDeleteEvidence,
  useDeleteFolder,
  useEvidenceList,
  useFolders,
  useUploadEvidence,
} from "../../evidence/hooks";
import { RiskItemPanel } from "../components/RiskItemPanel";
import { useCloseRiskItem } from "../hooks";

vi.mock("../../evidence/hooks");
vi.mock("../hooks");

const openRow: SheetRow = {
  id: 42,
  sheet_id: 1,
  row_index: 1,
  data: { category: "Bias", description: "Model may rank candidates unevenly." },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function mockDocumentBrowserHooks() {
  vi.mocked(useFolders).mockReturnValue({ data: [], isLoading: false } as never);
  vi.mocked(useCreateFolder).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useDeleteFolder).mockReturnValue({ mutateAsync: vi.fn(), isPending: false } as never);
  vi.mocked(useUploadEvidence).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
  vi.mocked(useDeleteEvidence).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as never);
}

function mockHooks({
  evidenceCount = 0,
  closeMutateAsync = vi.fn(),
  closeIsError = false,
  closeError,
}: {
  evidenceCount?: number;
  closeMutateAsync?: ReturnType<typeof vi.fn>;
  closeIsError?: boolean;
  closeError?: unknown;
} = {}) {
  mockDocumentBrowserHooks();
  vi.mocked(useEvidenceList).mockReturnValue({
    data: Array.from({ length: evidenceCount }, (_, i) => ({
      id: i,
      filename: `file-${i}.pdf`,
    })),
    isLoading: false,
  } as never);
  vi.mocked(useCloseRiskItem).mockReturnValue({
    mutateAsync: closeMutateAsync,
    isPending: false,
    isError: closeIsError,
    error: closeError,
  } as never);
}

describe("RiskItemPanel", () => {
  it("shows the item's category and description", () => {
    mockHooks();

    render(<RiskItemPanel riskAssessmentId={1} row={openRow} onClose={vi.fn()} />);

    expect(screen.getByText("Bias")).toBeInTheDocument();
    expect(screen.getByText("Model may rank candidates unevenly.")).toBeInTheDocument();
  });

  it("explains why closing is blocked when there is no evidence", () => {
    mockHooks({ evidenceCount: 0 });

    render(<RiskItemPanel riskAssessmentId={1} row={openRow} onClose={vi.fn()} />);

    expect(
      screen.getByText(/Attach at least one piece of evidence before this risk item can be closed/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark Risk Closed" })).not.toBeInTheDocument();
  });

  it("enables closing once evidence is attached", async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockHooks({ evidenceCount: 1, closeMutateAsync: mutateAsync });
    const user = userEvent.setup();

    render(<RiskItemPanel riskAssessmentId={1} row={openRow} onClose={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Mark Risk Closed" }));

    expect(mutateAsync).toHaveBeenCalledWith(42);
  });

  it("shows the server's error if closing fails", async () => {
    mockHooks({
      evidenceCount: 1,
      closeIsError: true,
      closeError: new ApiError(400, JSON.stringify({ detail: "nope" })),
    });

    render(<RiskItemPanel riskAssessmentId={1} row={openRow} onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("nope");
    });
  });

  it("shows a closed message instead of the evidence uploader once closed", () => {
    mockHooks({ evidenceCount: 1 });
    const closedRow: SheetRow = {
      ...openRow,
      data: { ...openRow.data, status: "closed", closed_at: "2026-02-01T00:00:00Z" },
    };

    render(<RiskItemPanel riskAssessmentId={1} row={closedRow} onClose={vi.fn()} />);

    expect(screen.getByText(/This risk item is closed/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mark Risk Closed" })).not.toBeInTheDocument();
  });

  it("calls onClose when the panel's close button is clicked", async () => {
    mockHooks();
    const onClose = vi.fn();
    const user = userEvent.setup();

    render(<RiskItemPanel riskAssessmentId={1} row={openRow} onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: "Close panel" }));

    expect(onClose).toHaveBeenCalled();
  });
});
