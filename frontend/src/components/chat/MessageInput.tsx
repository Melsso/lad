import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { createChat, sendMessage } from "../../services/chat";

interface MessageInputProps {
  chatId: number | null;
  onMessageSent?: () => void;
}

export function MessageInput({ chatId, onMessageSent }: MessageInputProps) {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = message.trim();
    if (!content || sending) {
      return;
    }

    setSending(true);

    try {
      let selectedChatId = chatId;
      if (selectedChatId === null) {
        const chat = await createChat(content);
        selectedChatId = chat.id;
      }

      await sendMessage({
        chat_id: selectedChatId,
        msg: content,
      });

      setMessage("");

      navigate(`/chat/${selectedChatId}`);

      onMessageSent?.();
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Message LAD..."
        disabled={sending}
      />

      <button type="submit" disabled={!message.trim() || sending}>
        {sending ? "..." : "Send"}
      </button>
    </form>
  );
}
