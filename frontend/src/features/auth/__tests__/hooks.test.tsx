import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { authApi } from "../api";
import { currentUserKey, useCurrentUser, useLogout } from "../hooks";

vi.mock("../api");

describe("useLogout", () => {
  it("makes a mounted useCurrentUser observer re-fetch and see the logged-out state", async () => {
    // Regression: this used to call queryClient.clear(), which wiped the
    // cache but didn't reliably push a re-fetch to an already-mounted
    // observer -- AuthGate kept rendering the dashboard after clicking
    // Sign Out until the page was manually reloaded. resetQueries() both
    // clears the cache and re-fetches active (mounted) queries.
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const user = { id: 1, name: "Ada", email: "ada@example.com" };
    vi.mocked(authApi.me).mockResolvedValue(user as never);
    vi.mocked(authApi.logout).mockResolvedValue(undefined);

    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const currentUser = renderHook(() => useCurrentUser(), { wrapper });
    await waitFor(() => expect(currentUser.result.current.data).toEqual(user));

    const logout = renderHook(() => useLogout(), { wrapper });
    vi.mocked(authApi.me).mockRejectedValue(new Error("Not authenticated"));
    logout.result.current.mutate();

    await waitFor(() => {
      expect(currentUser.result.current.isError).toBe(true);
    });
    expect(queryClient.getQueryData(currentUserKey)).toBeUndefined();
  });
});
