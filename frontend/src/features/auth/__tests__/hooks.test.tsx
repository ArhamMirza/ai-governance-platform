import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../../../shared/api/httpClient";
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
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(401, "Not authenticated"));
    logout.result.current.mutate();

    await waitFor(() => {
      expect(currentUser.result.current.data).toBeNull();
    });
    expect(queryClient.getQueryData(currentUserKey)).toBeNull();
  });
});

describe("useCurrentUser", () => {
  function wrapperFor(queryClient: QueryClient) {
    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  it("resolves to null, not an error, when there's no session", async () => {
    const queryClient = new QueryClient();
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(401, "Not authenticated"));

    const { result } = renderHook(() => useCurrentUser(), { wrapper: wrapperFor(queryClient) });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("stays settled through a background refetch while logged out", async () => {
    // Regression: as an error with no data, every refetch (window focus, a
    // component mounting) put the query back to pending, so AuthGate swapped
    // the sign-in form for its loading screen and wiped what was typed.
    const queryClient = new QueryClient();
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(401, "Not authenticated"));
    const seenLoading: boolean[] = [];

    const { result } = renderHook(
      () => {
        const query = useCurrentUser();
        seenLoading.push(query.isLoading);
        return query;
      },
      { wrapper: wrapperFor(queryClient) },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    seenLoading.length = 0;

    await act(() => queryClient.refetchQueries({ queryKey: currentUserKey }));

    expect(vi.mocked(authApi.me).mock.calls.length).toBeGreaterThanOrEqual(2);
    expect(seenLoading).not.toContain(true);
    expect(result.current.data).toBeNull();
  });

  it("still reports a real failure, like the server being unreachable, as an error", async () => {
    const queryClient = new QueryClient();
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(500, "Internal Server Error"));

    const { result } = renderHook(() => useCurrentUser(), { wrapper: wrapperFor(queryClient) });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
