import { useEffect, useState } from "react";

import { getChats } from "../services/chat";
import type { Chat } from "../types/chat";

interface UseChatsResult {
  chats: Chat[];
  loading: boolean;
  error: Error | null;
}

export function useChats(): UseChatsResult {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadChats() {
      try {
        const result = await getChats();

        if (!cancelled) {
          setChats(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Failed to load chats"),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadChats();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    chats,
    loading,
    error,
  };
}
