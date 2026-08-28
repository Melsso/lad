import { api } from "./api";
import type { Chat, ChatMessage, SendMessageRequest } from "../types/chat";

export function getChats(): Promise<Chat[]> {
  return api<Chat[]>("/app/");
}

export function getChatMessages(chatId: number): Promise<ChatMessage[]> {
  return api<ChatMessage[]>(`/chat/messages?chat_id=${chatId}`);
}

export function createChat(title?: string): Promise<Chat> {
  return api<Chat>("/chat/create", {
    method: "POST",
    body: JSON.stringify({
      title,
    }),
  });
}

export function updateChatTitle(chatId: number, title: string): Promise<Chat> {
  return api<Chat>(`/chat/title`, {
    method: "PATCH",
    body: JSON.stringify({
      chat_id: chatId,
      title,
    }),
  });
}

export function sendMessage(request: SendMessageRequest): Promise<ChatMessage> {
  return api<ChatMessage>("/chat/msg", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
