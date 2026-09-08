import type { Chat } from "../types/chat";

type ChatCreatedListener = (chat: Chat) => void;

const listeners = new Set<ChatCreatedListener>();

export function onChatCreated(listener: ChatCreatedListener): () => void {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function emitChatCreated(chat: Chat): void {
  for (const listener of listeners) {
    listener(chat);
  }
}
