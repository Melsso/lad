import { api } from "./api";
import type {
  Chat,
  ChatMessage,
  SendMessageRequest,
  StreamMessageHandlers,
} from "../types/chat";

const API_BASE_URL = "/api";

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

export function deleteChat(chatId: number): Promise<void> {
  return api<void>(`/chat/${chatId}`, {
    method: "DELETE",
  });
}

function processEvent(rawEvent: string, handlers: StreamMessageHandlers) {
  const lines = rawEvent.split("\n");
  let eventType = "message";
  let data = "";

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data = line.slice(5).trim();
    }
  }

  if (!data) {
    return;
  }

  const parsed = JSON.parse(data);

  if (eventType === "chunk") {
    handlers.onChunk(parsed.text as string);
  } else if (eventType === "done") {
    handlers.onDone(parsed as ChatMessage);
  } else if (eventType === "error") {
    handlers.onError(parsed.detail as string);
  }
}

async function consumeSseStream(
  url: string,
  body: unknown,
  handlers: StreamMessageHandlers,
): Promise<void> {
  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      signal: handlers.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }

    handlers.onError("Could not reach the server.");
    return;
  }

  if (!response.ok || !response.body) {
    handlers.onError("Failed to send message.");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();

      if (done) {
        buffer += decoder.decode();

        if (buffer.trim()) {
          processEvent(buffer, handlers);
        }

        break;
      }

      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const rawEvent of events) {
        processEvent(rawEvent, handlers);
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }

    handlers.onError("Connection lost while receiving the response.");
  }
}

export function streamMessage(
  request: SendMessageRequest,
  handlers: StreamMessageHandlers,
): Promise<void> {
  return consumeSseStream(`${API_BASE_URL}/chat/msg/stream`, request, handlers);
}

export function retryMessage(
  chatId: number,
  handlers: StreamMessageHandlers,
): Promise<void> {
  return consumeSseStream(
    `${API_BASE_URL}/chat/msg/retry`,
    { chat_id: chatId },
    handlers,
  );
}
