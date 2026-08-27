import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useCurrentUser } from "../../auth/hooks";
import { useAuditLog } from "../hooks";
import { useCanApprove } from "../useCanApprove";
import type { AuditLogEntry } from "../types";

vi.mock("../../auth/hooks");
vi.mock("../hooks");

const admin = { id: 1, name: "Admin", email: "admin@example.com", role: "admin", is_active: true, created_at: "" };
const contributor = { ...admin, id: 2, role: "contributor" };

function entry(overrides: Partial<AuditLogEntry>): AuditLogEntry {
  return {
    id: 1,
    entity_type: "Policy",
    entity_id: 1,
    action: "created",
    actor_id: null,
    timestamp: "2026-01-01T00:00:00Z",
    diff: null,
    ...overrides,
  };
}

function mockAuditLog(entries: AuditLogEntry[]) {
  vi.mocked(useAuditLog).mockReturnValue({ data: entries } as never);
}

function renderCanApprove() {
  const queryClient = createTestQueryClient();
  return renderHook(() => useCanApprove("Policy", 1), {
    wrapper: ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    ),
  });
}

describe("useCanApprove", () => {
  it("denies a contributor regardless of who submitted", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: contributor } as never);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
    expect(result.current.reason).toMatch(/admin/i);
  });

  it("denies an admin who submitted their own policy", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
    expect(result.current.reason).toMatch(/different user/i);
  });

  it("allows an admin who did not submit it", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: contributor.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(true);
    });
    expect(result.current.reason).toBeNull();
  });

  it("uses the most recent submission when there were several", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockAuditLog([
      entry({ id: 1, action: "submitted_for_review", actor_id: contributor.id }),
      entry({ id: 2, action: "submitted_for_review", actor_id: admin.id }),
    ]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
  });
});
