import { api } from "./api";
import type { Chat, ChatMessage, SendMessageRequest } from "../types/chat";

export function getChats(): Promise<Chat[]> {
  return api<Chat[]>("/chats");
}

export function getChatMessages(chatId: number): Promise<ChatMessage[]> {
  return api<ChatMessage[]>(`/chat/?chat_id=${chatId}`);
}

export function sendMessage(request: SendMessageRequest): Promise<ChatMessage> {
  return api<ChatMessage>("/chat/msg-resp", {
    method: "POST",
    body: JSON.stringify(request),
  });
}
