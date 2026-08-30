import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatList } from "../../src/components/chat/ChatList";
import { makeChat } from "./test-utils";

vi.mock("../../src/hooks/useChats");
vi.mock("../../src/services/chat");

import { useChats } from "../../src/hooks/useChats";
import { deleteChat, updateChatTitle } from "../../src/services/chat";

const mockedUseChats = vi.mocked(useChats);
const mockedUpdateChatTitle = vi.mocked(updateChatTitle);
const mockedDeleteChat = vi.mocked(deleteChat);

function LocationDisplay() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

function renderChatList(initialRoute = "/chat/1") {
  const page = (
    <>
      <ChatList />
      <LocationDisplay />
    </>
  );

  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route path="/chat" element={page} />
        <Route path="/chat/:chatId" element={page} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockChats(overrides: Partial<ReturnType<typeof useChats>> = {}) {
  mockedUseChats.mockReturnValue({
    chats: [
      makeChat({ id: 1, title: "First chat" }),
      makeChat({ id: 2, title: "Second chat" }),
    ],
    loading: false,
    error: null,
    refetch: vi.fn(),
    updateLocalChat: vi.fn(),
    removeLocalChat: vi.fn(),
    ...overrides,
  });
}

describe("ChatList", () => {
  afterEach(() => {
    mockedUseChats.mockReset();
    mockedUpdateChatTitle.mockReset();
    mockedDeleteChat.mockReset();
  });

  it("renders the chat list", () => {
    mockChats();

    renderChatList();

    expect(screen.getByText("First chat")).toBeInTheDocument();
    expect(screen.getByText("Second chat")).toBeInTheDocument();
  });

  it("shows a loading state", () => {
    mockChats({ loading: true, chats: [] });

    renderChatList();

    expect(screen.getByText("loading_chats...")).toBeInTheDocument();
  });

  it("shows an empty state", () => {
    mockChats({ chats: [] });

    renderChatList();

    expect(screen.getByText("no chats yet.")).toBeInTheDocument();
  });

  it("renames a chat and calls updateLocalChat on success", async () => {
    const user = userEvent.setup();
    const updateLocalChat = vi.fn();
    mockChats({ updateLocalChat });
    mockedUpdateChatTitle.mockResolvedValue(
      makeChat({ id: 1, title: "Renamed" }),
    );

    renderChatList();

    await user.click(screen.getByRole("button", { name: "Rename First chat" }));

    const input = screen.getByDisplayValue("First chat");
    await user.clear(input);
    await user.type(input, "Renamed");
    await user.click(screen.getByRole("button", { name: "✓" }));

    await waitFor(() =>
      expect(mockedUpdateChatTitle).toHaveBeenCalledWith(1, "Renamed"),
    );
    expect(updateLocalChat).toHaveBeenCalledWith(1, { title: "Renamed" });
  });

  it("shows an error when renaming fails", async () => {
    const user = userEvent.setup();
    mockChats();
    mockedUpdateChatTitle.mockRejectedValue(new Error("boom"));

    renderChatList();

    await user.click(screen.getByRole("button", { name: "Rename First chat" }));
    await user.click(screen.getByRole("button", { name: "✓" }));

    expect(await screen.findByText(/rename failed/)).toBeInTheDocument();
  });

  it("cancels renaming without calling the API", async () => {
    const user = userEvent.setup();
    mockChats();

    renderChatList();

    await user.click(screen.getByRole("button", { name: "Rename First chat" }));
    await user.click(screen.getByRole("button", { name: "×" }));

    expect(mockedUpdateChatTitle).not.toHaveBeenCalled();
    expect(screen.getByText("First chat")).toBeInTheDocument();
  });

  it("deletes a chat via the inline confirm and calls removeLocalChat", async () => {
    const user = userEvent.setup();
    const removeLocalChat = vi.fn();
    mockChats({ removeLocalChat });
    mockedDeleteChat.mockResolvedValue(undefined);

    renderChatList("/chat/2");

    await user.click(screen.getByRole("button", { name: "Delete First chat" }));
    expect(screen.getByText("delete this chat?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "yes" }));

    await waitFor(() => expect(mockedDeleteChat).toHaveBeenCalledWith(1));
    expect(removeLocalChat).toHaveBeenCalledWith(1);
  });

  it("navigates to /chat when deleting the currently active chat", async () => {
    const user = userEvent.setup();
    mockChats();
    mockedDeleteChat.mockResolvedValue(undefined);

    renderChatList("/chat/1");

    await user.click(screen.getByRole("button", { name: "Delete First chat" }));
    await user.click(screen.getByRole("button", { name: "yes" }));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("/chat"),
    );
  });

  it("does not navigate when deleting a chat that is not active", async () => {
    const user = userEvent.setup();
    mockChats();
    mockedDeleteChat.mockResolvedValue(undefined);

    renderChatList("/chat/2");

    await user.click(screen.getByRole("button", { name: "Delete First chat" }));
    await user.click(screen.getByRole("button", { name: "yes" }));

    await waitFor(() => expect(mockedDeleteChat).toHaveBeenCalled());
    expect(screen.getByTestId("location")).toHaveTextContent("/chat/2");
  });

  it("shows an error when deleting fails", async () => {
    const user = userEvent.setup();
    mockChats();
    mockedDeleteChat.mockRejectedValue(new Error("boom"));

    renderChatList();

    await user.click(screen.getByRole("button", { name: "Delete First chat" }));
    await user.click(screen.getByRole("button", { name: "yes" }));

    expect(await screen.findByText(/delete failed/)).toBeInTheDocument();
  });

  it("cancels deleting without calling the API", async () => {
    const user = userEvent.setup();
    mockChats();

    renderChatList();

    await user.click(screen.getByRole("button", { name: "Delete First chat" }));
    await user.click(screen.getByRole("button", { name: "×" }));

    expect(mockedDeleteChat).not.toHaveBeenCalled();
    expect(screen.getByText("First chat")).toBeInTheDocument();
  });
});
