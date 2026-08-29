import { useEffect, useRef } from "react";

import type { ChatMessage as ChatMessageType } from "../../types/chat";
import { ChatMessage } from "./ChatMessage";

interface ChatWindowProps {
  messages: ChatMessageType[];
  loading: boolean;
  streamingText: string;
  isStreaming: boolean;
}

export function ChatWindow({
  messages,
  loading,
  streamingText,
  isStreaming,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  return (
    <div className="h-full min-h-0 overflow-y-auto px-8 py-8">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {loading ? (
          <p className="font-mono text-xs text-text-dim">loading_messages...</p>
        ) : (
          messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))
        )}

        {isStreaming && (
          <ChatMessage
            pending
            message={{
              id: -1,
              chat_id: 0,
              role: "assistant",
              content: streamingText,
              created_at: new Date().toISOString(),
            }}
          />
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
