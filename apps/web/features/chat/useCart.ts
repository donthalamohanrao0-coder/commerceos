"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { SessionCart } from "@/lib/types";

/** The current cart for a chat session. `turn` (the number of turns so far) is
 *  part of the key so the cart refetches after every agent turn. */
export function useCart(sessionId: string | null, turn: number) {
  return useQuery({
    queryKey: ["session-cart", sessionId, turn],
    queryFn: () => api<SessionCart>(`/agent/sessions/${sessionId}/cart`),
    enabled: !!sessionId,
    placeholderData: (prev) => prev,
  });
}
