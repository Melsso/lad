import { useCallback, useEffect, useRef, useState } from "react";

import {
  createChat,
  getChatMessages,
  retryMessage,
  streamMessage,
} from "../services/chat";
import type { ChatMessage, StreamMessageHandlers } from "../types/chat";

interface UseChatStreamResult {
  messages: ChatMessage[];
  loading: boolean;
  streamingText: string;
  isStreaming: boolean;
  error: string | null;
  sendMessage: (content: string) => void;
  retry: () => void;
}

type LastAttempt =
  { mode: "resend"; content: string } | { mode: "regenerate"; chatId: number };

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
  const lastAttemptRef = useRef<LastAttempt | null>(null);

  useEffect(() => {
    activeChatIdRef.current = chatId;
    abortRef.current?.abort();
    lastAttemptRef.current = null;
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
        if (cancelled) {
          return;
        }

        setMessages(result);

        const lastMessage = result[result.length - 1];

        if (lastMessage && lastMessage.role === "user") {
          lastAttemptRef.current = { mode: "regenerate", chatId };
          setError("No reply was generated for this message.");
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

  const beginStream = useCallback(
    (
      requestChatId: number | null,
      streamer: (handlers: StreamMessageHandlers) => Promise<void>,
      onSettled?: () => void,
    ) => {
      const isStillActive = () => activeChatIdRef.current === requestChatId;

      async function run() {
        if (isStillActive()) {
          setStreamingText("");
          setIsStreaming(true);
        }

        const controller = new AbortController();
        if (isStillActive()) {
          abortRef.current = controller;
        }

        try {
          await streamer({
            signal: controller.signal,
            onChunk: (text) => {
              if (isStillActive()) {
                setStreamingText((current) => current + text);
              }
            },
            onToolCall: (message) => {
              if (isStillActive()) {
                setMessages((current) => [...current, message]);
              }
            },
            onToolResult: (message) => {
              if (isStillActive()) {
                setMessages((current) => [...current, message]);
              }
            },
            onDone: (message) => {
              if (isStillActive()) {
                setMessages((current) => [...current, message]);
                setStreamingText("");
                setIsStreaming(false);
              }

              lastAttemptRef.current = null;
              onSettled?.();
            },
            onError: (detail) => {
              if (isStillActive()) {
                setError(detail);
                setStreamingText("");
                setIsStreaming(false);
              }

              onSettled?.();
            },
          });
        } catch (err) {
          if (err instanceof DOMException && err.name === "AbortError") {
            return;
          }

          if (isStillActive()) {
            setError("Message failed to send. Try again.");
            setStreamingText("");
            setIsStreaming(false);
          }

          onSettled?.();
        }
      }

      void run();
    },
    [],
  );

  const sendMessage = useCallback(
    (content: string) => {
      const requestChatId = chatId;

      async function prepare() {
        let targetChatId = requestChatId;
        let didCreateChat = false;

        if (targetChatId === null) {
          try {
            const chat = await createChat(content);
            targetChatId = chat.id;
            didCreateChat = true;
          } catch {
            lastAttemptRef.current = { mode: "resend", content };

            if (activeChatIdRef.current === requestChatId) {
              setError("Could not start a new chat. Try again.");
            }
            return;
          }
        }

        lastAttemptRef.current = { mode: "regenerate", chatId: targetChatId };

        if (activeChatIdRef.current === requestChatId) {
          const optimisticMessage: ChatMessage = {
            id: -Date.now(),
            chat_id: targetChatId,
            content,
            role: "user",
            created_at: new Date().toISOString(),
          };

          setMessages((current) => [...current, optimisticMessage]);
        }

        beginStream(
          requestChatId,
          (handlers) =>
            streamMessage(
              { chat_id: targetChatId as number, msg: content },
              handlers,
            ),
          () => {
            if (didCreateChat && activeChatIdRef.current === requestChatId) {
              onChatCreated(targetChatId as number);
            }
          },
        );
      }

      void prepare();
    },
    [chatId, onChatCreated, beginStream],
  );

  const retry = useCallback(() => {
    const attempt = lastAttemptRef.current;

    if (!attempt) {
      return;
    }

    setError(null);

    if (attempt.mode === "resend") {
      sendMessage(attempt.content);
      return;
    }

    beginStream(attempt.chatId, (handlers) =>
      retryMessage(attempt.chatId, handlers),
    );
  }, [sendMessage, beginStream]);

  return {
    messages,
    loading,
    streamingText,
    isStreaming,
    error,
    sendMessage,
    retry,
  };
}
