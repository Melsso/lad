import { useEffect, useRef, useState } from "react";

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
  const bottomRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="h-full min-h-0 overflow-y-auto px-8 py-8">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {loading ? (
          <p className="font-mono text-xs text-text-dim">loading_messages...</p>
        ) : (
          messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
