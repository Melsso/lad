import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { ChatWindow } from "../components/chat/ChatWindow";
import { MessageInput } from "../components/chat/MessageInput";
import { useChatStream } from "../hooks/useChatStream";

export function ChatPage() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const selectedChatId = chatId ? Number(chatId) : null;

  const handleChatCreated = useCallback(
    (newChatId: number) => {
      navigate(`/chat/${newChatId}`, { replace: true });
    },
    [navigate],
  );

  const { messages, loading, streamingText, isStreaming, error, sendMessage } =
    useChatStream(selectedChatId, handleChatCreated);

  const hasContent =
    selectedChatId !== null || messages.length > 0 || isStreaming;

  return (
    <AppLayout>
      <div className="flex h-full min-h-0 flex-col">
        {hasContent ? (
          <ChatWindow
            messages={messages}
            loading={loading}
            streamingText={streamingText}
            isStreaming={isStreaming}
          />
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 px-8 text-center">
            <h2 className="font-display text-2xl font-semibold tracking-wide text-text-primary">
              LAD is listening<span className="text-magenta">.</span>
            </h2>
            <p className="max-w-sm font-mono text-xs text-text-dim">
              start a new conversation below to boot up a session.
            </p>
          </div>
        )}

        <MessageInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          error={error}
        />
      </div>
    </AppLayout>
  );
}
