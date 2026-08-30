import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createChat,
  deleteChat,
  getChatMessages,
  getChats,
  retryMessage,
  streamMessage,
  updateChatTitle,
} from "../../src/services/chat";
import { createSseResponse, makeMessage, sseEvent } from "./test-utils";

vi.mock("../../src/services/api");

import { api } from "../../src/services/api";

const mockedApi = vi.mocked(api);

describe("chat CRUD functions", () => {
  afterEach(() => {
    mockedApi.mockReset();
  });

  it("getChats calls the app listing endpoint", async () => {
    mockedApi.mockResolvedValue([]);

    await getChats();

    expect(mockedApi).toHaveBeenCalledWith("/app/");
  });

  it("getChatMessages includes the chat_id query param", async () => {
    mockedApi.mockResolvedValue([]);

    await getChatMessages(42);

    expect(mockedApi).toHaveBeenCalledWith("/chat/messages?chat_id=42");
  });

  it("createChat posts the title as the request body", async () => {
    mockedApi.mockResolvedValue({});

    await createChat("hello there");

    expect(mockedApi).toHaveBeenCalledWith(
      "/chat/create",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ title: "hello there" }),
      }),
    );
  });

  it("updateChatTitle PATCHes chat_id and title", async () => {
    mockedApi.mockResolvedValue({});

    await updateChatTitle(7, "New Title");

    expect(mockedApi).toHaveBeenCalledWith(
      "/chat/title",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ chat_id: 7, title: "New Title" }),
      }),
    );
  });

  it("deleteChat DELETEs the chat by id", async () => {
    mockedApi.mockResolvedValue(undefined);

    await deleteChat(9);

    expect(mockedApi).toHaveBeenCalledWith(
      "/chat/9",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("streamMessage / retryMessage (SSE consumption)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("delivers chunk events to onChunk in order", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          createSseResponse([
            sseEvent("chunk", { text: "Hel" }),
            sseEvent("chunk", { text: "lo" }),
            sseEvent("done", {
              id: 1,
              chat_id: 1,
              role: "assistant",
              content: "Hello",
              created_at: "2026-01-01T00:00:00Z",
            }),
          ]),
        ),
    );

    const chunks: string[] = [];
    const onChunk = vi.fn((text: string) => chunks.push(text));
    const onDone = vi.fn();
    const onError = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk, onDone, onError },
    );

    expect(chunks).toEqual(["Hel", "lo"]);
    expect(onDone).toHaveBeenCalledWith(
      expect.objectContaining({ id: 1, content: "Hello" }),
    );
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onError with the server-provided detail on an error event", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          createSseResponse([
            sseEvent("error", { detail: "Failed to generate a response" }),
          ]),
        ),
    );

    const onError = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk: vi.fn(), onDone: vi.fn(), onError },
    );

    expect(onError).toHaveBeenCalledWith("Failed to generate a response");
  });

  it("handles an event split across multiple network reads", async () => {
    const full = sseEvent("chunk", { text: "hello" });
    const splitPoint = Math.floor(full.length / 2);

    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          createSseResponse([
            full.slice(0, splitPoint),
            full.slice(splitPoint),
          ]),
        ),
    );

    const onChunk = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk, onDone: vi.fn(), onError: vi.fn() },
    );

    expect(onChunk).toHaveBeenCalledWith("hello");
  });

  it("flushes a final event that has no trailing blank line before the stream closes", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          createSseResponse([
            'event: chunk\ndata: {"text": "no trailing newline"}',
          ]),
        ),
    );

    const onChunk = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk, onDone: vi.fn(), onError: vi.fn() },
    );

    expect(onChunk).toHaveBeenCalledWith("no trailing newline");
  });

  it("calls onError when fetch itself rejects", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("network down")),
    );

    const onError = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk: vi.fn(), onDone: vi.fn(), onError },
    );

    expect(onError).toHaveBeenCalledWith("Could not reach the server.");
  });

  it("re-throws AbortError instead of calling onError", async () => {
    const abortError = new DOMException("aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortError));

    const onError = vi.fn();

    await expect(
      streamMessage(
        { chat_id: 1, msg: "hi" },
        { onChunk: vi.fn(), onDone: vi.fn(), onError },
      ),
    ).rejects.toThrow("aborted");

    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onError when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 500 })),
    );

    const onError = vi.fn();

    await streamMessage(
      { chat_id: 1, msg: "hi" },
      { onChunk: vi.fn(), onDone: vi.fn(), onError },
    );

    expect(onError).toHaveBeenCalledWith("Failed to send message.");
  });

  it("retryMessage posts to the retry endpoint with only chat_id", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(createSseResponse([sseEvent("done", makeMessage())]));
    vi.stubGlobal("fetch", fetchMock);

    await retryMessage(5, {
      onChunk: vi.fn(),
      onDone: vi.fn(),
      onError: vi.fn(),
    });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/chat/msg/retry");
    expect(JSON.parse(options.body)).toEqual({ chat_id: 5 });
  });
});
