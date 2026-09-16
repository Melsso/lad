import { describe, expect, it } from "vitest";

import {
  describeToolCall,
  groupMessagesForDisplay,
  isToolResultFailure,
  toolLabel,
} from "../../src/context/toolActivity";
import { makeMessage } from "./test-utils";

describe("toolLabel", () => {
  it("maps known tool names to a human label", () => {
    expect(toolLabel("run_command")).toBe("Ran a command");
    expect(toolLabel("web_search")).toBe("Searched the web");
    expect(toolLabel("recall_memory")).toBe("Searched past conversations");
  });

  it("falls back to the raw name for unknown tools", () => {
    expect(toolLabel("mystery_tool")).toBe("mystery_tool");
  });

  it("falls back to a generic label when the name is missing", () => {
    expect(toolLabel(null)).toBe("Tool");
    expect(toolLabel(undefined)).toBe("Tool");
  });
});

describe("describeToolCall", () => {
  it("describes a run_command call with its command", () => {
    const call = makeMessage({
      role: "tool_call",
      tool_name: "run_command",
      tool_arguments: '{"command":"ls -la"}',
    });

    expect(describeToolCall(call)).toBe("Ran `ls -la`");
  });

  it("describes a web_search call with its query", () => {
    const call = makeMessage({
      role: "tool_call",
      tool_name: "web_search",
      tool_arguments: '{"query":"weather in Tokyo"}',
    });

    expect(describeToolCall(call)).toBe(
      'Searched the web for "weather in Tokyo"',
    );
  });

  it("describes a recall_memory call with its query", () => {
    const call = makeMessage({
      role: "tool_call",
      tool_name: "recall_memory",
      tool_arguments: '{"query":"manga"}',
    });

    expect(describeToolCall(call)).toBe(
      'Searched past conversations for "manga"',
    );
  });

  it("falls back to the tool label when arguments are missing or malformed", () => {
    const noArgs = makeMessage({ role: "tool_call", tool_name: "web_search" });
    const badArgs = makeMessage({
      role: "tool_call",
      tool_name: "web_search",
      tool_arguments: "not json",
    });

    expect(describeToolCall(noArgs)).toBe("Searched the web");
    expect(describeToolCall(badArgs)).toBe("Searched the web");
  });
});

describe("isToolResultFailure", () => {
  it("is false when there is no result yet", () => {
    expect(isToolResultFailure(null)).toBe(false);
  });

  it("treats an Error-prefixed result as a failure", () => {
    const result = makeMessage({
      role: "tool_result",
      content: "Error calling run_command: boom",
    });

    expect(isToolResultFailure(result)).toBe(true);
  });

  it("treats a non-zero exit_code as a failure", () => {
    const result = makeMessage({
      role: "tool_result",
      content: "exit_code: 127\nstdout:\n\nstderr:\nnot found",
    });

    expect(isToolResultFailure(result)).toBe(true);
  });

  it("treats a zero exit_code as success", () => {
    const result = makeMessage({
      role: "tool_result",
      content: "exit_code: 0\nstdout:\nhi\nstderr:\n",
    });

    expect(isToolResultFailure(result)).toBe(false);
  });

  it("treats an empty-results message as success, not failure", () => {
    const result = makeMessage({
      role: "tool_result",
      content: "No results found.",
    });

    expect(isToolResultFailure(result)).toBe(false);
  });
});

describe("groupMessagesForDisplay", () => {
  it("pairs an adjacent tool_call and tool_result into one tool item", () => {
    const call = makeMessage({ id: 1, role: "tool_call" });
    const result = makeMessage({ id: 2, role: "tool_result" });

    const items = groupMessagesForDisplay([call, result]);

    expect(items).toEqual([{ kind: "tool", call, result }]);
  });

  it("keeps ordinary messages as message items around a tool pair", () => {
    const user = makeMessage({ id: 1, role: "user", content: "hi" });
    const call = makeMessage({ id: 2, role: "tool_call" });
    const result = makeMessage({ id: 3, role: "tool_result" });
    const assistant = makeMessage({
      id: 4,
      role: "assistant",
      content: "done",
    });

    const items = groupMessagesForDisplay([user, call, result, assistant]);

    expect(items).toEqual([
      { kind: "message", message: user },
      { kind: "tool", call, result },
      { kind: "message", message: assistant },
    ]);
  });

  it("renders a trailing tool_call with no result yet as a running tool item", () => {
    const call = makeMessage({ id: 1, role: "tool_call" });

    const items = groupMessagesForDisplay([call]);

    expect(items).toEqual([{ kind: "tool", call, result: null }]);
  });

  it("drops an orphaned tool_result with no preceding call", () => {
    const result = makeMessage({ id: 1, role: "tool_result" });
    const user = makeMessage({ id: 2, role: "user", content: "hi" });

    const items = groupMessagesForDisplay([result, user]);

    expect(items).toEqual([{ kind: "message", message: user }]);
  });
});
