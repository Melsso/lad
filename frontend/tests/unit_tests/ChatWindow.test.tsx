import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatWindow } from "../../src/components/chat/ChatWindow";
import { makeMessage } from "./test-utils";

describe("ChatWindow", () => {
  it("renders a paired tool_call/tool_result as a single tool activity item", () => {
    render(
      <ChatWindow
        messages={[
          makeMessage({ id: 1, role: "user", content: "search something" }),
          makeMessage({ id: 2, role: "tool_call", tool_name: "web_search" }),
          makeMessage({ id: 3, role: "tool_result", content: "results" }),
        ]}
        loading={false}
        streamingText=""
        isStreaming={false}
        error={null}
        onRetry={vi.fn()}
        mode="chat"
      />,
    );

    expect(screen.getByText("search something")).toBeInTheDocument();
    expect(screen.getByText("Searched the web")).toBeInTheDocument();
    expect(screen.queryByText("results")).not.toBeInTheDocument();
  });

  it("passes agent mode through so tool detail renders", () => {
    render(
      <ChatWindow
        messages={[
          makeMessage({
            id: 1,
            role: "tool_call",
            tool_name: "run_command",
            tool_arguments: '{"command":"ls"}',
          }),
          makeMessage({
            id: 2,
            role: "tool_result",
            content: "exit_code: 0\nstdout:\nok\nstderr:\n",
          }),
        ]}
        loading={false}
        streamingText=""
        isStreaming={false}
        error={null}
        onRetry={vi.fn()}
        mode="agent"
      />,
    );

    expect(screen.getByText("Ran `ls`")).toBeInTheDocument();
  });

  it("defaults to chat-mode rendering when no mode prop is given", () => {
    render(
      <ChatWindow
        messages={[
          makeMessage({
            id: 1,
            role: "tool_call",
            tool_name: "run_command",
            tool_arguments: '{"command":"ls"}',
          }),
          makeMessage({
            id: 2,
            role: "tool_result",
            content: "exit_code: 0\nstdout:\nok\nstderr:\n",
          }),
        ]}
        loading={false}
        streamingText=""
        isStreaming={false}
        error={null}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.queryByText("Ran `ls`")).not.toBeInTheDocument();
    expect(screen.getByText("Ran a command")).toBeInTheDocument();
  });

  it("shows the loading indicator instead of messages while loading", () => {
    render(
      <ChatWindow
        messages={[makeMessage({ id: 1, content: "hidden while loading" })]}
        loading={true}
        streamingText=""
        isStreaming={false}
        error={null}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.getByText("loading_messages...")).toBeInTheDocument();
    expect(screen.queryByText("hidden while loading")).not.toBeInTheDocument();
  });
});
