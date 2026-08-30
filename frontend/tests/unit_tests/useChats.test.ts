import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useChats } from "../../src/hooks/useChats";
import { makeChat } from "./test-utils";

vi.mock("../../src/services/chat");

import { getChats } from "../../src/services/chat";

const mockedGetChats = vi.mocked(getChats);

describe("useChats", () => {
  afterEach(() => {
    mockedGetChats.mockReset();
  });

  it("starts in a loading state and populates chats on success", async () => {
    const chats = [makeChat({ id: 1 }), makeChat({ id: 2 })];
    mockedGetChats.mockResolvedValue(chats);

    const { result } = renderHook(() => useChats());

    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.chats).toEqual(chats);
    expect(result.current.error).toBeNull();
  });

  it("sets an error when loading fails", async () => {
    mockedGetChats.mockRejectedValue(new Error("boom"));

    const { result } = renderHook(() => useChats());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).not.toBeNull();
    expect(result.current.chats).toEqual([]);
  });

  it("refetch reloads the chat list", async () => {
    mockedGetChats.mockResolvedValueOnce([makeChat({ id: 1, title: "First" })]);

    const { result } = renderHook(() => useChats());

    await waitFor(() => expect(result.current.loading).toBe(false));

    mockedGetChats.mockResolvedValueOnce([
      makeChat({ id: 1, title: "First" }),
      makeChat({ id: 2, title: "Second" }),
    ]);

    await act(async () => {
      await result.current.refetch();
    });

    expect(result.current.chats).toHaveLength(2);
  });

  it("updateLocalChat patches a chat without a network call", async () => {
    mockedGetChats.mockResolvedValue([makeChat({ id: 1, title: "Old" })]);

    const { result } = renderHook(() => useChats());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.updateLocalChat(1, { title: "New" });
    });

    expect(result.current.chats[0].title).toBe("New");
    expect(mockedGetChats).toHaveBeenCalledTimes(1);
  });

  it("removeLocalChat removes a chat from local state", async () => {
    mockedGetChats.mockResolvedValue([
      makeChat({ id: 1 }),
      makeChat({ id: 2 }),
    ]);

    const { result } = renderHook(() => useChats());

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.removeLocalChat(1);
    });

    expect(result.current.chats.map((c) => c.id)).toEqual([2]);
  });
});
