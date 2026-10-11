import { useQuery } from "@tanstack/react-query";

import { staffApi } from "./api";

export const staffLibraryKey = ["staff", "library"] as const;

export function useStaffLibrary() {
  return useQuery({ queryKey: staffLibraryKey, queryFn: staffApi.library });
}
