import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { ChatPage } from "../../src/pages/ChatPage";
import {
  makeChat,
  makeMessage,
  renderWithRouter,
  sseEvent,
} from "../unit_tests/test-utils";
import { sseResponse } from "./handlers";
import { server } from "./server";

describe("chat flow (real components + faked network)", () => {
  it("loads an existing chat and renders markdown content", async () => {
    server.use(
      http.get("/api/chat/messages", () =>
        HttpResponse.json([
          makeMessage({ id: 1, role: "user", content: "explain pi" }),
          makeMessage({
            id: 2,
            role: "assistant",
            content: "**Pi** is the constant $\\pi$",
          }),
        ]),
      ),
    );

    renderWithRouter(<ChatPage />, "/chat/1");

    expect(await screen.findByText("Pi")).toBeInTheDocument();
    expect(screen.getByText("Pi").tagName).toBe("STRONG");

    const { container } = { container: document.body };
    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("sends a message on a brand-new chat and renders the streamed reply", async () => {
    const user = userEvent.setup();

    server.use(
      http.post("/api/chat/msg/stream", () =>
        sseResponse([
          sseEvent("chunk", { text: "General" }),
          sseEvent("chunk", { text: " Kenobi" }),
          sseEvent(
            "done",
            makeMessage({
              id: 2,
              role: "assistant",
              content: "General Kenobi",
            }),
          ),
        ]),
      ),
      http.get("/api/chat/messages", () =>
        HttpResponse.json([
          makeMessage({ id: 1, role: "user", content: "Hello there" }),
          makeMessage({ id: 2, role: "assistant", content: "General Kenobi" }),
        ]),
      ),
    );

    renderWithRouter(<ChatPage />, "/chat");

    const input = await screen.findByPlaceholderText("Message LAD...");
    await user.type(input, "Hello there");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(
      await screen.findByText("Hello there", {}, { timeout: 7000 }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("General Kenobi", {}, { timeout: 7000 }),
    ).toBeInTheDocument();
  });

  it("detects a dangling user message and completes it via retry", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/chat/messages", () =>
        HttpResponse.json([
          makeMessage({ id: 1, role: "user", content: "unanswered question" }),
        ]),
      ),
      http.post("/api/chat/msg/retry", () =>
        sseResponse([
          sseEvent(
            "done",
            makeMessage({
              id: 2,
              role: "assistant",
              content: "here is the answer",
            }),
          ),
        ]),
      ),
    );

    renderWithRouter(<ChatPage />, "/chat/1");

    expect(
      await screen.findByText("No reply was generated for this message."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("here is the answer")).toBeInTheDocument();
  });

  it("deleting the active chat returns to the empty state", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/app/", () =>
        HttpResponse.json([makeChat({ id: 1, title: "Chat One" })]),
      ),
      http.get("/api/chat/messages", () =>
        HttpResponse.json([
          makeMessage({ id: 1, role: "user", content: "hi" }),
        ]),
      ),
    );

    renderWithRouter(<ChatPage />, "/chat/1");

    const sidebarItem = await screen.findByText("Chat One");
    const listItem = sidebarItem.closest("li") as HTMLElement;

    await user.click(
      within(listItem).getByRole("button", { name: "Delete Chat One" }),
    );
    await user.click(within(listItem).getByRole("button", { name: "yes" }));

    await waitFor(() =>
      expect(screen.getByText(/LAD is listening/)).toBeInTheDocument(),
    );
  });
});
