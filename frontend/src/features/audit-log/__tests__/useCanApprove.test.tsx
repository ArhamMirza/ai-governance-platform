import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createTestQueryClient } from "../../../test/testQueryClient";
import { useCurrentUser } from "../../auth/hooks";
import { useCaigoDelegation } from "../../governance-roles/hooks";
import { useUserDirectory } from "../../users/hooks";
import { useAuditLog } from "../hooks";
import { useCanApprove } from "../useCanApprove";
import type { AuditLogEntry } from "../types";

vi.mock("../../auth/hooks");
vi.mock("../../governance-roles/hooks");
vi.mock("../../users/hooks");
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

function mockDirectory(caigoUserId: number | null) {
  vi.mocked(useUserDirectory).mockReturnValue({
    data: [
      {
        id: admin.id,
        name: admin.name,
        governance_roles: caigoUserId === admin.id ? ["Chief AI Governance Officer"] : [],
      },
      {
        id: contributor.id,
        name: contributor.name,
        governance_roles: caigoUserId === contributor.id ? ["Chief AI Governance Officer"] : [],
      },
    ],
  } as never);
}

/** No active delegation unless a test says otherwise -- matches "nobody has
 * been delegated CAIGO" being the default state in a real org. */
function mockDelegation(delegateUserId: number | null) {
  vi.mocked(useCaigoDelegation).mockReturnValue({
    data:
      delegateUserId === null
        ? null
        : {
            id: 1,
            delegate_user_id: delegateUserId,
            delegate_name: "Delegate",
            starts_at: "2026-01-01T00:00:00Z",
            ends_at: "2026-02-01T00:00:00Z",
          },
  } as never);
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
  it("denies an admin who is not the Chief AI Governance Officer", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockDirectory(null);
    mockDelegation(null);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: contributor.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
    expect(result.current.reason).toMatch(/chief ai governance officer/i);
  });

  it("denies the CAIGO holder who submitted their own policy", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockDirectory(admin.id);
    mockDelegation(null);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
    expect(result.current.reason).toMatch(/different user/i);
  });

  it("allows the CAIGO holder who did not submit it", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockDirectory(admin.id);
    mockDelegation(null);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: contributor.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(true);
    });
    expect(result.current.reason).toBeNull();
  });

  it("uses the most recent submission when there were several", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: admin } as never);
    mockDirectory(admin.id);
    mockDelegation(null);
    mockAuditLog([
      entry({ id: 1, action: "submitted_for_review", actor_id: contributor.id }),
      entry({ id: 2, action: "submitted_for_review", actor_id: admin.id }),
    ]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
  });

  it("denies a contributor with no CAIGO role and no active delegation", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: contributor } as never);
    mockDirectory(null);
    mockDelegation(null);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
  });

  it("allows a standing-in delegate who does not hold the role directly", async () => {
    // Nobody in the directory holds Chief AI Governance Officer -- only an
    // active delegation makes the contributor CAIGO for this purpose, the
    // same way governance_role_service.is_caigo treats it on the backend.
    vi.mocked(useCurrentUser).mockReturnValue({ data: contributor } as never);
    mockDirectory(null);
    mockDelegation(contributor.id);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(true);
    });
    expect(result.current.reason).toBeNull();
  });

  it("still denies a delegate who submitted the thing themselves", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: contributor } as never);
    mockDirectory(null);
    mockDelegation(contributor.id);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: contributor.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
    expect(result.current.reason).toMatch(/different user/i);
  });

  it("does not let someone else's delegation make an unrelated user CAIGO", async () => {
    vi.mocked(useCurrentUser).mockReturnValue({ data: contributor } as never);
    mockDirectory(null);
    // Delegated to the admin, not the contributor rendering this hook.
    mockDelegation(admin.id);
    mockAuditLog([entry({ action: "submitted_for_review", actor_id: admin.id })]);

    const { result } = renderCanApprove();

    await waitFor(() => {
      expect(result.current.canApprove).toBe(false);
    });
  });
});
