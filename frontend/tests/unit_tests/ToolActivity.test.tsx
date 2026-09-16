import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ToolActivity } from "../../src/components/chat/ToolActivity";
import { makeMessage } from "./test-utils";

describe("ToolActivity", () => {
  it("chat mode shows only the tool label and status, never call or result detail", () => {
    const call = makeMessage({
      role: "tool_call",
      tool_name: "web_search",
      tool_arguments: '{"query":"weather in Tokyo"}',
    });
    const result = makeMessage({
      role: "tool_result",
      content: "some search result content",
    });

    render(<ToolActivity call={call} result={result} mode="chat" />);

    expect(screen.getByText("Searched the web")).toBeInTheDocument();
    expect(screen.getByText("— done")).toBeInTheDocument();
    expect(screen.queryByText("weather in Tokyo")).not.toBeInTheDocument();
    expect(
      screen.queryByText("some search result content"),
    ).not.toBeInTheDocument();
  });

  it("chat mode shows a running status when there is no result yet", () => {
    const call = makeMessage({ role: "tool_call", tool_name: "web_search" });

    render(<ToolActivity call={call} result={null} mode="chat" />);

    expect(screen.getByText("— running")).toBeInTheDocument();
  });

  it("agent mode shows the pretty call description and status without exposing raw JSON", () => {
    const call = makeMessage({
      role: "tool_call",
      tool_name: "run_command",
      tool_arguments: '{"command":"ls -la"}',
    });
    const result = makeMessage({
      role: "tool_result",
      content: "exit_code: 0\nstdout:\nfile.txt\nstderr:\n",
    });

    render(<ToolActivity call={call} result={result} mode="agent" />);

    expect(screen.getByText("Ran `ls -la`")).toBeInTheDocument();
    expect(screen.getByText("done")).toBeInTheDocument();
    expect(screen.queryByText('{"command":"ls -la"}')).not.toBeInTheDocument();
  });

  it("agent mode expands to show the full result content on click", async () => {
    const user = userEvent.setup();
    const call = makeMessage({ role: "tool_call", tool_name: "run_command" });
    const result = makeMessage({
      role: "tool_result",
      content: "exit_code: 0\nstdout:\nhello from the sandbox\nstderr:\n",
    });

    render(<ToolActivity call={call} result={result} mode="agent" />);

    expect(
      screen.queryByText(/hello from the sandbox/),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button"));

    expect(screen.getByText(/hello from the sandbox/)).toBeInTheDocument();
  });

  it("agent mode marks a failed run_command result", () => {
    const call = makeMessage({ role: "tool_call", tool_name: "run_command" });
    const result = makeMessage({
      role: "tool_result",
      content: "exit_code: 127\nstdout:\n\nstderr:\nnot found",
    });

    render(<ToolActivity call={call} result={result} mode="agent" />);

    expect(screen.getByText("failed")).toBeInTheDocument();
  });

  it("agent mode is not expandable while the tool is still running", () => {
    const call = makeMessage({ role: "tool_call", tool_name: "run_command" });

    render(<ToolActivity call={call} result={null} mode="agent" />);

    expect(screen.getByRole("button")).toBeDisabled();
  });
});
