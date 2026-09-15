import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { type ConversationStart, assistantApi } from "./api";

export const conversationsKey = ["assistant", "conversations"];
export const conversationKey = (id: number) => ["assistant", "conversation", id];

export function useConversations(enabled: boolean) {
  return useQuery({ queryKey: conversationsKey, queryFn: assistantApi.list, enabled });
}

export function useConversation(id: number | null) {
  return useQuery({
    queryKey: conversationKey(id ?? 0),
    queryFn: () => assistantApi.get(id as number),
    enabled: id !== null,
  });
}

export function useStartConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ConversationStart) => assistantApi.start(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: conversationsKey }),
  });
}

export function useAsk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, question }: { id: number; question: string }) =>
      assistantApi.ask(id, question),
    onSuccess: (_answer, { id }) => {
      queryClient.invalidateQueries({ queryKey: conversationKey(id) });
      // The first question names the conversation, and every answer moves it
      // to the top of the history.
      queryClient.invalidateQueries({ queryKey: conversationsKey });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => assistantApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: conversationsKey }),
  });
}
