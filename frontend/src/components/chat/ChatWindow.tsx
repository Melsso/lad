import { useEffect, useState } from "react";

import { getChatMessages } from "../../services/chat";
import type { ChatMessage } from "../../types/chat";
import { ChatMessage as ChatMessageComponent } from "./ChatMessage";

interface ChatWindowProps {
  chatId: number;
  refreshKey: number;
}

export function ChatWindow({ chatId, refreshKey }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadMessages() {
      setLoading(true);

      try {
        const result = await getChatMessages(chatId);

        if (!cancelled) {
          setMessages(result);
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
  }, [chatId, refreshKey]);

  return (
    <div className="chat-window">
      {loading ? (
        <div>Loading...</div>
      ) : (
        messages.map((message) => (
          <ChatMessageComponent key={message.id} message={message} />
        ))
      )}
    </div>
  );
}
