import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatModeSelector } from "../../src/components/chat/ChatModeSelector";

describe("ChatModeSelector", () => {
  it("marks the currently selected mode as pressed", () => {
    render(<ChatModeSelector mode="chat" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Chat" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Agent" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("calls onChange with the clicked mode", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    render(<ChatModeSelector mode="chat" onChange={onChange} />);

    await user.click(screen.getByRole("button", { name: "Agent" }));

    expect(onChange).toHaveBeenCalledWith("agent");
  });

  it("disables both buttons when disabled is true", () => {
    render(<ChatModeSelector mode="chat" onChange={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Chat" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Agent" })).toBeDisabled();
  });
});
