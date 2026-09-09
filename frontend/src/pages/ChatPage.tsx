import { useCallback, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { ChatModeSelector } from "../components/chat/ChatModeSelector";
import { ChatWindow } from "../components/chat/ChatWindow";
import { MessageInput } from "../components/chat/MessageInput";
import { useChatStream } from "../hooks/useChatStream";
import { useFavicon } from "../hooks/useFavicon";

export function ChatPage() {
  const { chatId } = useParams();
  const navigate = useNavigate();
  const selectedChatId = chatId ? Number(chatId) : null;
  const [newChatMode, setNewChatMode] = useState<"chat" | "agent">("chat");

  const handleChatCreated = useCallback(
    (newChatId: number) => {
      navigate(`/chat/${newChatId}`, { replace: true });
    },
    [navigate],
  );

  const {
    messages,
    loading,
    streamingText,
    isStreaming,
    error,
    sendMessage,
    retry,
  } = useChatStream(selectedChatId, handleChatCreated);
  useFavicon(isStreaming);

  const hasContent =
    selectedChatId !== null ||
    messages.length > 0 ||
    isStreaming ||
    error !== null;

  return (
    <AppLayout>
      <div className="flex h-full min-h-0 flex-col">
        {hasContent ? (
          <ChatWindow
            messages={messages}
            loading={loading}
            streamingText={streamingText}
            isStreaming={isStreaming}
            error={error}
            onRetry={retry}
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

        {!hasContent && (
          <ChatModeSelector mode={newChatMode} onChange={setNewChatMode} />
        )}

        <MessageInput
          onSend={(content) => sendMessage(content, newChatMode)}
          isStreaming={isStreaming}
        />
      </div>
    </AppLayout>
  );
}
