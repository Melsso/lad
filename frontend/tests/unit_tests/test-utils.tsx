import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import type { Chat, ChatMessage } from "../../src/types/chat";

export function renderWithRouter(ui: ReactElement, route = "/chat") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/chat" element={ui} />
        <Route path="/chat/:chatId" element={ui} />
      </Routes>
    </MemoryRouter>,
  );
}

export function makeChat(overrides: Partial<Chat> = {}): Chat {
  return {
    id: 1,
    title: "Test Chat",
    mode: "chat",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 1,
    chat_id: 1,
    role: "user",
    content: "hello",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function createSseResponse(
  chunks: string[],
  options: { status?: number; ok?: boolean; noBody?: boolean } = {},
): Response {
  if (options.noBody) {
    return new Response(null, { status: options.status ?? 200 });
  }

  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return new Response(body, {
    status: options.status ?? 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

export function sseEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}
