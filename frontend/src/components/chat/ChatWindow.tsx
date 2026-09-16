import { useEffect, useRef } from "react";

import type { ChatMessage as ChatMessageType } from "../../types/chat";
import { groupMessagesForDisplay } from "../../context/toolActivity";
import { ChatMessage } from "./ChatMessage";
import { ToolActivity } from "./ToolActivity";

interface ChatWindowProps {
  messages: ChatMessageType[];
  loading: boolean;
  streamingText: string;
  isStreaming: boolean;
  error: string | null;
  onRetry: () => void;
  mode?: "chat" | "agent";
}

export function ChatWindow({
  messages,
  loading,
  streamingText,
  isStreaming,
  error,
  onRetry,
  mode = "chat",
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, error]);

  const renderItems = groupMessagesForDisplay(messages);

  return (
    <div className="h-full min-h-0 overflow-y-auto px-8 py-8">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {loading ? (
          <p className="font-mono text-xs text-text-dim">loading_messages...</p>
        ) : (
          renderItems.map((item) =>
            item.kind === "message" ? (
              <ChatMessage key={item.message.id} message={item.message} />
            ) : (
              <ToolActivity
                key={item.call.id}
                call={item.call}
                result={item.result}
                mode={mode}
              />
            ),
          )
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

        {!isStreaming && error && (
          <div className="flex flex-col items-start gap-2">
            <div className="mb-1 font-mono text-[10px] tracking-[0.2em] text-magenta uppercase">
              system
            </div>

            <div className="flex max-w-[75ch] items-center gap-3 rounded-lg border border-magenta/40 bg-panel-alt/60 px-4 py-3 text-sm text-text-primary">
              <span className="h-2 w-2 shrink-0 rounded-full bg-magenta shadow-[0_0_8px_var(--color-magenta)]" />
              <span className="flex-1">{error}</span>
              <button
                type="button"
                onClick={onRetry}
                className="shrink-0 rounded-md border border-magenta/50 px-3 py-1 font-mono text-xs tracking-wide text-magenta uppercase transition hover:bg-magenta/10"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
