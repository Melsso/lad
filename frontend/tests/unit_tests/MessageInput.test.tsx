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

    expect(onSend).toHaveBeenCalledWith("hello there");
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
});
