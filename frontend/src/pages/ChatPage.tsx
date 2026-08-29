import { useParams } from "react-router-dom";
import { useState } from "react";

import { AppLayout } from "../components/layout/AppLayout";
import { ChatWindow } from "../components/chat/ChatWindow";
import { MessageInput } from "../components/chat/MessageInput";

export function ChatPage() {
  const { chatId } = useParams();
  const [refreshKey, setRefreshKey] = useState(0);
  const selectedChatId = chatId ? Number(chatId) : null;

  return (
    <AppLayout>
      <div className="flex h-full min-h-0 flex-col">
        {selectedChatId !== null ? (
          <ChatWindow chatId={selectedChatId} refreshKey={refreshKey} />
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
          chatId={selectedChatId}
          onMessageSent={() => setRefreshKey((key) => key + 1)}
        />
      </div>
    </AppLayout>
  );
}
