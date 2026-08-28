import { useEffect, useState } from "react";

import { getChatMessages } from "../../services/chat";
import type { ChatMessage } from "../../types/chat";
import { ChatMessage as ChatMessageComponent } from "./ChatMessage";

interface ChatWindowProps {
  chatId: number | null;
}

export function ChatWindow({ chatId }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (chatId === null) {
      return;
    }

    const selectedChatId = chatId;

    let cancelled = false;

    async function loadMessages() {
      setLoading(true);
      setError(null);

      try {
        const result = await getChatMessages(selectedChatId);

        if (!cancelled) {
          setMessages(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err : new Error("Failed to load messages"),
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadMessages();

    return () => {
      cancelled = true;
    };
  }, [chatId]);

  if (chatId === null) {
    return (
      <div className="chat-window empty">
        <p>Select a chat to get started.</p>
      </div>
    );
  }

  return (
    <div className="chat-window">
      {loading && <p>Loading...</p>}

      {error && <p>Failed to load messages.</p>}

      {!loading && !error && (
        <div className="messages">
          {messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}
        </div>
      )}
    </div>
  );
}
