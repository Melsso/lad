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
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = message.trim();
    if (!content || sending) {
      return;
    }

    setSending(true);
    setError(null);

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
    } catch {
      setError("Message failed to send. Try again.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-8 pb-6">
      {error && <p className="mb-2 font-mono text-xs text-magenta">{error}</p>}

      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 rounded-lg border bg-panel-alt px-3 py-2 transition-colors ${
          sending
            ? "border-amber/50"
            : "border-line focus-within:border-cyan/60"
        }`}
      >
        {sending && (
          <span className="h-2 w-2 shrink-0 animate-pulse-glow rounded-full bg-amber shadow-[0_0_10px_var(--color-amber)]" />
        )}

        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Message LAD..."
          disabled={sending}
          className="min-w-0 flex-1 bg-transparent py-2 text-sm text-text-primary outline-none placeholder:text-text-dim disabled:opacity-60"
        />

        <button
          type="submit"
          disabled={!message.trim() || sending}
          className="shrink-0 rounded-md bg-magenta px-4 py-2 font-mono text-xs tracking-wide text-void uppercase transition hover:shadow-[0_0_14px_rgba(255,61,142,0.5)] disabled:cursor-not-allowed disabled:bg-line disabled:text-text-dim disabled:shadow-none"
        >
          {sending ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
