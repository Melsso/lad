import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MessageInput } from "../../src/components/chat/MessageInput";

describe("MessageInput", () => {
  it("calls onSend with the trimmed message and clears the input", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<MessageInput onSend={onSend} isStreaming={false} />);

    const input = screen.getByPlaceholderText("Message LAD...");
    await user.type(input, "  hello there  ");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("hello there", []);
    expect(input).toHaveValue("");
  });

  it("does not call onSend for empty or whitespace-only input", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<MessageInput onSend={onSend} isStreaming={false} />);

    const input = screen.getByPlaceholderText("Message LAD...");
    await user.type(input, "   ");

    expect(screen.getByRole("button")).toBeDisabled();

    await user.keyboard("{Enter}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables the input and button while streaming", () => {
    render(<MessageInput onSend={vi.fn()} isStreaming={true} />);

    expect(screen.getByPlaceholderText("Message LAD...")).toBeDisabled();
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("does not call onSend when submitted while streaming", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    const { rerender } = render(
      <MessageInput onSend={onSend} isStreaming={false} />,
    );

    const input = screen.getByPlaceholderText("Message LAD...");
    await user.type(input, "queued message");

    rerender(<MessageInput onSend={onSend} isStreaming={true} />);

    await user.keyboard("{Enter}");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not render the attach-files button in chat mode", () => {
    render(<MessageInput onSend={vi.fn()} isStreaming={false} mode="chat" />);

    expect(
      screen.queryByRole("button", { name: "Attach files" }),
    ).not.toBeInTheDocument();
  });

  it("renders the attach-files button in agent mode", () => {
    render(<MessageInput onSend={vi.fn()} isStreaming={false} mode="agent" />);

    expect(
      screen.getByRole("button", { name: "Attach files" }),
    ).toBeInTheDocument();
  });

  it("attaches a selected file and sends it alongside the message", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<MessageInput onSend={onSend} isStreaming={false} mode="agent" />);

    const file = new File(["print(1)"], "main.py", { type: "text/plain" });
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;

    await user.upload(fileInput, file);

    expect(screen.getByText("main.py")).toBeInTheDocument();

    const input = screen.getByPlaceholderText("Message LAD...");
    await user.type(input, "analyze this");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(onSend).toHaveBeenCalledWith("analyze this", [file]);
    expect(screen.queryByText("main.py")).not.toBeInTheDocument();
  });

  it("rejects a disallowed file extension with an inline error", async () => {
    const user = userEvent.setup();

    render(<MessageInput onSend={vi.fn()} isStreaming={false} mode="agent" />);

    const file = new File(["bad"], "virus.exe", {
      type: "application/octet-stream",
    });
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;

    await user.upload(fileInput, file);

    expect(
      screen.getByText(/is not supported: virus\.exe/),
    ).toBeInTheDocument();
    expect(screen.queryByText("virus.exe")).not.toBeInTheDocument();
  });

  it("allows removing a selected file before sending", async () => {
    const user = userEvent.setup();

    render(<MessageInput onSend={vi.fn()} isStreaming={false} mode="agent" />);

    const file = new File(["print(1)"], "main.py", { type: "text/plain" });
    const fileInput = document.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;

    await user.upload(fileInput, file);
    expect(screen.getByText("main.py")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove main.py" }));

    expect(screen.queryByText("main.py")).not.toBeInTheDocument();
  });
});
