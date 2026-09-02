import { HttpResponse, http } from "msw";

import { makeChat } from "../unit_tests/test-utils";

export function sseResponse(events: string[]) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(event));
      }
      controller.close();
    },
  });

  return new HttpResponse(stream, {
    headers: { "Content-Type": "text/event-stream" },
  });
}

export const handlers = [
  http.get("/api/app/", () => HttpResponse.json([])),
  http.get("/api/chat/messages", () => HttpResponse.json([])),
  http.post("/api/chat/create", async ({ request }) => {
    const body = (await request.json()) as { title?: string };
    return HttpResponse.json(
      makeChat({ id: 1, title: body.title ?? "New Chat" }),
    );
  }),
  http.patch("/api/chat/title", async ({ request }) => {
    const body = (await request.json()) as { chat_id: number; title: string };
    return HttpResponse.json(makeChat({ id: body.chat_id, title: body.title }));
  }),
  http.delete("/api/chat/:chatId", () =>
    HttpResponse.json({ status: "deleted" }),
  ),
];
