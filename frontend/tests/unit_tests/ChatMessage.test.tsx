import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessage } from "../../src/components/chat/ChatMessage";
import { makeMessage } from "./test-utils";

describe("ChatMessage", () => {
  it("renders plain text content", () => {
    render(<ChatMessage message={makeMessage({ content: "hello world" })} />);

    expect(screen.getByText("hello world")).toBeInTheDocument();
  });

  it("renders markdown bold and links", () => {
    render(
      <ChatMessage
        message={makeMessage({
          content: "this is **bold** and a [link](https://example.com)",
        })}
      />,
    );

    expect(screen.getByText("bold").tagName).toBe("STRONG");

    const link = screen.getByRole("link", { name: "link" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("shows the role label", () => {
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "hi" })}
      />,
    );

    expect(screen.getByText("assistant")).toBeInTheDocument();
  });

  it("shows a thinking indicator when pending with no content yet", () => {
    const { container } = render(
      <ChatMessage pending message={makeMessage({ content: "" })} />,
    );

    expect(container.querySelector(".animate-pulse-glow")).not.toBeNull();
  });

  it("shows a blinking cursor when pending with partial content", () => {
    const { container } = render(
      <ChatMessage pending message={makeMessage({ content: "partial" })} />,
    );

    expect(screen.getByText("partial")).toBeInTheDocument();
    expect(container.querySelector(".animate-blink")).not.toBeNull();
  });

  it("does not show a cursor when not pending", () => {
    const { container } = render(
      <ChatMessage message={makeMessage({ content: "done" })} />,
    );

    expect(container.querySelector(".animate-blink")).toBeNull();
  });

  it("renders headings", () => {
    render(
      <ChatMessage
        message={makeMessage({
          content: "# Title\n\n## Subtitle\n\n### Small",
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Title" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Subtitle" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: "Small" }),
    ).toBeInTheDocument();
  });

  it("renders unordered and ordered lists", () => {
    render(
      <ChatMessage
        message={makeMessage({
          content: "- one\n- two\n\n1. first\n2. second",
        })}
      />,
    );

    expect(screen.getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByText("one").closest("ul")).not.toBeNull();
    expect(screen.getByText("first").closest("ol")).not.toBeNull();
  });

  it("renders a blockquote", () => {
    render(
      <ChatMessage message={makeMessage({ content: "> a quoted line" })} />,
    );

    const quote = screen.getByText("a quoted line");
    expect(quote.closest("blockquote")).not.toBeNull();
  });

  it("renders an inline code span and a fenced code block", () => {
    render(
      <ChatMessage
        message={makeMessage({
          content: "use `inline()` then:\n\n```js\nconsole.log(1)\n```",
        })}
      />,
    );

    expect(screen.getByText("inline()").tagName).toBe("CODE");
    expect(screen.getByText("console.log(1)").closest("pre")).not.toBeNull();
  });

  it("renders a GFM table", () => {
    render(
      <ChatMessage
        message={makeMessage({
          content: "| A | B |\n| --- | --- |\n| 1 | 2 |",
        })}
      />,
    );

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "A" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "1" })).toBeInTheDocument();
  });

  it("renders a tool_call message as a compact chip with parsed arguments", () => {
    render(
      <ChatMessage
        message={makeMessage({
          role: "tool_call",
          content: "",
          tool_name: "get_temperature",
          tool_arguments: '{"city":"New York"}',
        })}
      />,
    );

    expect(screen.getByText("get_temperature")).toBeInTheDocument();
    expect(screen.getByText('{"city":"New York"}')).toBeInTheDocument();
  });

  it("renders a tool_result message as a compact chip with the result content", () => {
    render(
      <ChatMessage
        message={makeMessage({
          role: "tool_result",
          content: "22°C",
          tool_name: "get_temperature",
        })}
      />,
    );

    expect(screen.getByText("get_temperature")).toBeInTheDocument();
    expect(screen.getByText("22°C")).toBeInTheDocument();
  });
});
