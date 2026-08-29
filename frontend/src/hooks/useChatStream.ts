import { useCallback, useEffect, useRef, useState } from "react";

import { createChat, getChatMessages, streamMessage } from "../services/chat";
import type { ChatMessage } from "../types/chat";

interface UseChatStreamResult {
  messages: ChatMessage[];
  loading: boolean;
  streamingText: string;
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string) => void;
}

export function useChatStream(
  chatId: number | null,
  onChatCreated: (chatId: number) => void,
): UseChatStreamResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeChatIdRef = useRef<number | null>(chatId);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    activeChatIdRef.current = chatId;
    abortRef.current?.abort();
    setIsStreaming(false);
    setStreamingText("");
    setError(null);

    let cancelled = false;

    if (chatId === null) {
      setMessages([]);
      setLoading(false);
      return;
    }

    setLoading(true);

    getChatMessages(chatId)
      .then((result) => {
        if (!cancelled) {
          setMessages(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load messages.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [chatId]);

  const sendMessage = useCallback(
    (content: string) => {
      const requestChatId = chatId;

      async function run() {
        let targetChatId = requestChatId;
        let didCreateChat = false;

        if (targetChatId === null) {
          try {
            const chat = await createChat(content);
            targetChatId = chat.id;
            didCreateChat = true;
          } catch {
            if (activeChatIdRef.current === requestChatId) {
              setError("Could not start a new chat. Try again.");
            }
            return;
          }
        }

        const isStillActive = () => activeChatIdRef.current === requestChatId;

        const optimisticMessage: ChatMessage = {
          id: -Date.now(),
          chat_id: targetChatId,
          content,
          role: "user",
          created_at: new Date().toISOString(),
        };

        if (isStillActive()) {
          setMessages((current) => [...current, optimisticMessage]);
          setStreamingText("");
          setIsStreaming(true);
        }

        const controller = new AbortController();
        if (isStillActive()) {
          abortRef.current = controller;
        }

        try {
          await streamMessage(
            { chat_id: targetChatId, msg: content },
            {
              signal: controller.signal,
              onChunk: (text) => {
                if (isStillActive()) {
                  setStreamingText((current) => current + text);
                }
              },
              onDone: (message) => {
                if (isStillActive()) {
                  setMessages((current) => [...current, message]);
                  setStreamingText("");
                  setIsStreaming(false);
                }

                if (didCreateChat && isStillActive()) {
                  onChatCreated(targetChatId as number);
                }
              },
              onError: (detail) => {
                if (isStillActive()) {
                  setError(detail);
                  setStreamingText("");
                  setIsStreaming(false);
                }

                if (didCreateChat && isStillActive()) {
                  onChatCreated(targetChatId as number);
                }
              },
            },
          );
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") {
            return;
          }

          if (isStillActive()) {
            setError("Message failed to send. Try again.");
            setStreamingText("");
            setIsStreaming(false);
          }

          if (didCreateChat && isStillActive()) {
            onChatCreated(targetChatId as number);
          }
        }
      }

      void run();
    },
    [chatId, onChatCreated],
  );

  return {
    messages,
    loading,
    streamingText,
    isStreaming,
    error,
    sendMessage,
  };
}
