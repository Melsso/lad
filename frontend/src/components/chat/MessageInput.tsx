import { useState } from "react";
import type { FormEvent } from "react";

interface MessageInputProps {
  onSend: (content: string) => void;
  isStreaming: boolean;
}

export function MessageInput({ onSend, isStreaming }: MessageInputProps) {
  const [message, setMessage] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const content = message.trim();
    if (!content || isStreaming) {
      return;
    }

    onSend(content);
    setMessage("");
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-8 pb-6">
      <form
        onSubmit={handleSubmit}
        className={`flex items-center gap-2 rounded-lg border bg-panel-alt px-3 py-2 transition-colors ${
          isStreaming
            ? "border-amber/50"
            : "border-line focus-within:border-cyan/60"
        }`}
      >
        {isStreaming && (
          <span className="h-2 w-2 shrink-0 animate-pulse-glow rounded-full bg-amber shadow-[0_0_10px_var(--color-amber)]" />
        )}

        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Message LAD..."
          disabled={isStreaming}
          className="min-w-0 flex-1 bg-transparent py-2 text-sm text-text-primary outline-none placeholder:text-text-dim disabled:opacity-60"
        />

        <button
          type="submit"
          disabled={!message.trim() || isStreaming}
          className="shrink-0 rounded-md bg-magenta px-4 py-2 font-mono text-xs tracking-wide text-void uppercase transition hover:shadow-[0_0_14px_rgba(255,61,142,0.5)] disabled:cursor-not-allowed disabled:bg-line disabled:text-text-dim disabled:shadow-none"
        >
          {isStreaming ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
