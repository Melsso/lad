import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useChatStream } from "../../src/hooks/useChatStream";
import type { StreamMessageHandlers } from "../../src/types/chat";
import { makeChat, makeMessage } from "./test-utils";

vi.mock("../../src/services/chat");

import {
  createChat,
  getChatMessages,
  retryMessage,
  streamMessage,
} from "../../src/services/chat";

const mockedCreateChat = vi.mocked(createChat);
const mockedGetChatMessages = vi.mocked(getChatMessages);
const mockedStreamMessage = vi.mocked(streamMessage);
const mockedRetryMessage = vi.mocked(retryMessage);

function controllableStreamer() {
  let handlers: StreamMessageHandlers | null = null;
  let resolve: (() => void) | null = null;

  const promise = new Promise<void>((res) => {
    resolve = res;
  });

  const fn = vi.fn((_request: unknown, h: StreamMessageHandlers) => {
    handlers = h;
    return promise;
  });

  return {
    fn,
    getHandlers: () => handlers,
    finish: () => resolve?.(),
  };
}

describe("useChatStream", () => {
  afterEach(() => {
    mockedCreateChat.mockReset();
    mockedGetChatMessages.mockReset();
    mockedStreamMessage.mockReset();
    mockedRetryMessage.mockReset();
  });

  it("loads existing messages for a given chat", async () => {
    const messages = [
      makeMessage({ id: 1, role: "user", content: "hi" }),
      makeMessage({ id: 2, role: "assistant", content: "hello" }),
    ];
    mockedGetChatMessages.mockResolvedValue(messages);

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.messages).toEqual(messages);
    expect(result.current.error).toBeNull();
  });

  it("detects a dangling unanswered user message and enables retry", async () => {
    mockedGetChatMessages.mockResolvedValue([
      makeMessage({ id: 1, role: "user", content: "unanswered" }),
    ]);
    mockedRetryMessage.mockResolvedValue(undefined);

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    await waitFor(() =>
      expect(result.current.error).toBe(
        "No reply was generated for this message.",
      ),
    );

    act(() => {
      result.current.retry();
    });

    await waitFor(() =>
      expect(mockedRetryMessage).toHaveBeenCalledWith(1, expect.anything()),
    );
    expect(mockedCreateChat).not.toHaveBeenCalled();
  });

  it("detects a turn that failed mid tool-call and enables retry", async () => {
    mockedGetChatMessages.mockResolvedValue([
      makeMessage({ id: 1, role: "user", content: "unzip this" }),
      makeMessage({ id: 2, role: "tool_call", content: "" }),
      makeMessage({ id: 3, role: "tool_result", content: "extracted" }),
    ]);
    mockedRetryMessage.mockResolvedValue(undefined);

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    await waitFor(() =>
      expect(result.current.error).toBe(
        "No reply was generated for this message.",
      ),
    );

    act(() => {
      result.current.retry();
    });

    await waitFor(() =>
      expect(mockedRetryMessage).toHaveBeenCalledWith(1, expect.anything()),
    );
  });

  it("sendMessage on an existing chat adds an optimistic message and streams the reply", async () => {
    mockedGetChatMessages.mockResolvedValue([]);
    const streamer = controllableStreamer();
    mockedStreamMessage.mockImplementation(streamer.fn);

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.sendMessage("hello there");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(true));
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0]).toMatchObject({
      role: "user",
      content: "hello there",
    });

    act(() => {
      streamer.getHandlers()?.onChunk("Hel");
      streamer.getHandlers()?.onChunk("lo");
    });

    expect(result.current.streamingText).toBe("Hello");

    act(() => {
      streamer
        .getHandlers()
        ?.onDone(makeMessage({ id: 2, role: "assistant", content: "Hello" }));
      streamer.finish();
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.streamingText).toBe("");
  });

  it("appends tool_call and tool_result messages as they arrive mid-stream", async () => {
    mockedGetChatMessages.mockResolvedValue([]);
    const streamer = controllableStreamer();
    mockedStreamMessage.mockImplementation(streamer.fn);

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.sendMessage("weather in NY?");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(true));

    act(() => {
      streamer.getHandlers()?.onToolCall?.(
        makeMessage({
          id: 2,
          role: "tool_call",
          content: "",
          tool_call_id: "call_0",
          tool_name: "get_temperature",
          tool_arguments: '{"city": "New York"}',
        }),
      );
    });

    expect(result.current.messages).toHaveLength(2);

    act(() => {
      streamer.getHandlers()?.onToolResult?.(
        makeMessage({
          id: 3,
          role: "tool_result",
          content: "22°C",
          tool_call_id: "call_0",
          tool_name: "get_temperature",
        }),
      );
    });

    expect(result.current.messages).toHaveLength(3);
    expect(result.current.messages[2]).toMatchObject({
      role: "tool_result",
      content: "22°C",
    });

    act(() => {
      streamer
        .getHandlers()
        ?.onDone(
          makeMessage({ id: 4, role: "assistant", content: "It's 22°C." }),
        );
      streamer.finish();
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(false));
    expect(result.current.messages).toHaveLength(4);
  });

  it("sendMessage on a new chat creates the chat before streaming and defers onChatCreated until done", async () => {
    mockedCreateChat.mockResolvedValue(makeChat({ id: 99 }));
    const streamer = controllableStreamer();
    mockedStreamMessage.mockImplementation(streamer.fn);
    const onChatCreated = vi.fn();

    const { result } = renderHook(() => useChatStream(null, onChatCreated));

    expect(result.current.loading).toBe(false);

    act(() => {
      result.current.sendMessage("first message");
    });

    await waitFor(() =>
      expect(mockedCreateChat).toHaveBeenCalledWith("first message", "chat"),
    );
    await waitFor(() => expect(mockedStreamMessage).toHaveBeenCalled());

    expect(onChatCreated).not.toHaveBeenCalled();

    act(() => {
      streamer.getHandlers()?.onDone(makeMessage({ id: 1, chat_id: 99 }));
      streamer.finish();
    });

    await waitFor(() => expect(onChatCreated).toHaveBeenCalledWith(99));
  });

  it("sendMessage on a new chat passes the selected agent mode through to createChat", async () => {
    mockedCreateChat.mockResolvedValue(makeChat({ id: 99, mode: "agent" }));
    const streamer = controllableStreamer();
    mockedStreamMessage.mockImplementation(streamer.fn);

    const { result } = renderHook(() => useChatStream(null, vi.fn()));

    act(() => {
      result.current.sendMessage("first message", "agent");
    });

    await waitFor(() =>
      expect(mockedCreateChat).toHaveBeenCalledWith("first message", "agent"),
    );
  });

  it("a createChat failure sets an error retryable by resending, preserving the selected mode", async () => {
    mockedCreateChat.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useChatStream(null, vi.fn()));

    act(() => {
      result.current.sendMessage("first message", "agent");
    });

    await waitFor(() =>
      expect(result.current.error).toBe(
        "Could not start a new chat. Try again.",
      ),
    );

    mockedCreateChat.mockResolvedValue(makeChat({ id: 5, mode: "agent" }));
    mockedStreamMessage.mockResolvedValue(undefined);

    act(() => {
      result.current.retry();
    });

    await waitFor(() =>
      expect(mockedCreateChat).toHaveBeenLastCalledWith(
        "first message",
        "agent",
      ),
    );
  });

  it("an LLM failure on an existing chat is retryable via regenerate, not resend", async () => {
    mockedGetChatMessages.mockResolvedValue([]);
    mockedStreamMessage.mockImplementation(async (_req, handlers) => {
      handlers.onError("Failed to generate a response");
    });

    const { result } = renderHook(() => useChatStream(1, vi.fn()));

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.sendMessage("hello");
    });

    await waitFor(() =>
      expect(result.current.error).toBe("Failed to generate a response"),
    );

    mockedRetryMessage.mockResolvedValue(undefined);

    act(() => {
      result.current.retry();
    });

    await waitFor(() =>
      expect(mockedRetryMessage).toHaveBeenCalledWith(1, expect.anything()),
    );
    expect(mockedCreateChat).not.toHaveBeenCalled();
  });

  it("ignores stream updates that arrive after switching to a different chat", async () => {
    mockedGetChatMessages.mockImplementation(async (chatId: number) =>
      chatId === 2
        ? [makeMessage({ id: 50, chat_id: 2, content: "chat two" })]
        : [],
    );

    const streamer = controllableStreamer();
    mockedStreamMessage.mockImplementation(streamer.fn);

    const { result, rerender } = renderHook(
      ({ chatId }) => useChatStream(chatId, vi.fn()),
      { initialProps: { chatId: 1 } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.sendMessage("hello from chat one");
    });

    await waitFor(() => expect(result.current.isStreaming).toBe(true));

    rerender({ chatId: 2 });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages).toEqual([
      expect.objectContaining({ id: 50, chat_id: 2 }),
    ]);

    act(() => {
      streamer.getHandlers()?.onChunk("late chunk");
      streamer.getHandlers()?.onDone(makeMessage({ id: 99, chat_id: 1 }));
      streamer.finish();
    });

    expect(result.current.streamingText).toBe("");
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages).toEqual([
      expect.objectContaining({ id: 50, chat_id: 2 }),
    ]);
  });
});
