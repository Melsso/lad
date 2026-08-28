import { useState } from "react";
import type { FormEvent } from "react";
import { sendMessage } from "../../services/chat";

interface MessageInputProps {
  chatId: number | null;
  onMessageSent?: () => void;
}

export function MessageInput({ chatId, onMessageSent }: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (chatId === null || !message.trim() || sending) {
      return;
    }

    const content = message.trim();

    setMessage("");
    setSending(true);

    try {
      await sendMessage({
        chat_id: chatId,
        msg: content,
      });

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
        placeholder={chatId === null ? "Select a chat..." : "Message LAD..."}
        disabled={chatId === null || sending}
      />

      <button
        type="submit"
        disabled={chatId === null || !message.trim() || sending}
      >
        {sending ? "..." : "Send"}
      </button>
    </form>
  );
}
