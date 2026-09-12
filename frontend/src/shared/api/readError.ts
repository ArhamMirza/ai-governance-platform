import { ApiError } from "./httpClient";

/** Every form/panel in the app reads a failed mutation's error the same
 * way: the backend's `detail` message if the response body parses as JSON,
 * otherwise the raw error text, falling back to a caller-supplied message
 * for anything that isn't an ApiError at all (a network failure, say). */
export function readError(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError)) return fallback;
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    return parsed.detail ?? err.message;
  } catch {
    return err.message || fallback;
  }
}
