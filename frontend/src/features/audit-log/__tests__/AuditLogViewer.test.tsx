import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { auditLogApi } from "../api";
import { AuditLogViewer } from "../components/AuditLogViewer";
import type { AuditLogEntry } from "../types";

vi.mock("../api");

function renderViewer() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <AuditLogViewer entityType="Policy" entityId={1} />
    </QueryClientProvider>,
  );
}

describe("AuditLogViewer", () => {
  it("renders each entry with its action, timestamp, and diff", async () => {
    const entries: AuditLogEntry[] = [
      {
        id: 1,
        entity_type: "Policy",
        entity_id: 1,
        action: "created",
        actor_id: null,
        timestamp: "2026-01-01T00:00:00Z",
        diff: { title: "Data Retention Policy" },
      },
      {
        id: 2,
        entity_type: "Policy",
        entity_id: 1,
        action: "approved",
        actor_id: null,
        timestamp: "2026-01-02T00:00:00Z",
        diff: null,
      },
    ];
    vi.mocked(auditLogApi.list).mockResolvedValue(entries);

    renderViewer();

    await waitFor(() => {
      expect(
        screen.getByText(/created.*\(title: Data Retention Policy\)/),
      ).toBeInTheDocument();
      expect(screen.getByText(/approved/)).toBeInTheDocument();
    });
  });

  it("shows an empty state when there is no history", async () => {
    vi.mocked(auditLogApi.list).mockResolvedValue([]);

    renderViewer();

    await waitFor(() => {
      expect(screen.getByText("No audit history yet.")).toBeInTheDocument();
    });
  });

  it("shows an error state when the request fails", async () => {
    vi.mocked(auditLogApi.list).mockRejectedValue(new Error("network error"));

    renderViewer();

    await waitFor(() => {
      expect(screen.getByText("Failed to load audit log.")).toBeInTheDocument();
    });
  });
});
