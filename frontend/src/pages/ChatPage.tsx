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
      <div
        className={`chat-page ${selectedChatId === null ? "chat-page-empty" : ""}`}
      >
        {selectedChatId !== null && (
          <ChatWindow chatId={selectedChatId} refreshKey={refreshKey} />
        )}

        <MessageInput
          chatId={selectedChatId}
          onMessageSent={() => setRefreshKey((key) => key + 1)}
        />
      </div>
    </AppLayout>
  );
}
