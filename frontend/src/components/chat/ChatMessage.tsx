import type { ChatMessage as ChatMessageType } from "../../types/chat";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <article className={`message message-${message.role}`}>
      <div className="message-role">{message.role}</div>

      <div className="message-content">{message.content}</div>
    </article>
  );
}
