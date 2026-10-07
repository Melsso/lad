import { useCallback, useEffect, useState } from "react";

import { getChats } from "../services/chat";
import { onChatCreated } from "../context/chatEvents";
import type { Chat } from "../types/chat";

interface UseChatsResult {
  chats: Chat[];
  loading: boolean;
  error: Error | null;
  updateLocalChat: (chatId: number, patch: Partial<Chat>) => void;
  removeLocalChat: (chatId: number) => void;
}

export function useChats(): UseChatsResult {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function initialLoad() {
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

    initialLoad();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return onChatCreated((chat) => {
      setChats((current) => {
        if (current.some((existing) => existing.id === chat.id)) {
          return current;
        }

        return [...current, chat];
      });
    });
  }, []);

  const updateLocalChat = useCallback(
    (chatId: number, patch: Partial<Chat>) => {
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId ? { ...chat, ...patch } : chat,
        ),
      );
    },
    [],
  );

  const removeLocalChat = useCallback((chatId: number) => {
    setChats((current) => current.filter((chat) => chat.id !== chatId));
  }, []);

  return {
    chats,
    loading,
    error,
    updateLocalChat,
    removeLocalChat,
  };
}
