import { useParams } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { ChatWindow } from "../components/chat/ChatWindow";
import { MessageInput } from "../components/chat/MessageInput";

export function ChatPage() {
  const { chatId } = useParams();

  const selectedChatId = chatId ? Number(chatId) : null;

  return (
    <AppLayout>
      <div className="chat-page">
        <ChatWindow chatId={selectedChatId} />

        <MessageInput chatId={selectedChatId} />
      </div>
    </AppLayout>
  );
}
