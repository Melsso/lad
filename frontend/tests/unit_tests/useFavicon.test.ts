import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { useFavicon } from "../../src/hooks/useFavicon";

const DEFAULT_ICON = "/favicon.svg";
const PROCESSING_ICON = "/favicon-processing.svg";
const READY_ICON = "/favicon-ready.svg";

function getIconHref(): string {
  const link = document.querySelector<HTMLLinkElement>("link[rel~='icon']");
  return link?.getAttribute("href") ?? "";
}

function setDocumentHidden(hidden: boolean) {
  Object.defineProperty(document, "hidden", {
    configurable: true,
    value: hidden,
  });
}

function clearFavicon() {
  document
    .querySelectorAll("link[rel~='icon']")
    .forEach((link) => link.remove());
}

describe("useFavicon", () => {
  afterEach(() => {
    clearFavicon();
    setDocumentHidden(false);
  });

  it("renders the default favicon when idle and the document is visible", () => {
    renderHook(({ isStreaming }) => useFavicon(isStreaming), {
      initialProps: { isStreaming: false },
    });

    expect(getIconHref()).toBe(DEFAULT_ICON);
  });

  it("switches to the processing favicon while streaming", () => {
    const { rerender } = renderHook(
      ({ isStreaming }) => useFavicon(isStreaming),
      { initialProps: { isStreaming: false } },
    );

    rerender({ isStreaming: true });

    expect(getIconHref()).toBe(PROCESSING_ICON);
  });

  it("shows the ready favicon when streaming completes while the tab is hidden", () => {
    setDocumentHidden(true);

    const { rerender } = renderHook(
      ({ isStreaming }) => useFavicon(isStreaming),
      { initialProps: { isStreaming: false } },
    );

    rerender({ isStreaming: true });
    rerender({ isStreaming: false });

    expect(getIconHref()).toBe(READY_ICON);
  });

  it("returns to the default favicon when streaming completes while the tab is visible", () => {
    const { rerender } = renderHook(
      ({ isStreaming }) => useFavicon(isStreaming),
      { initialProps: { isStreaming: true } },
    );

    rerender({ isStreaming: false });

    expect(getIconHref()).toBe(DEFAULT_ICON);
  });

  it("resets to the default favicon when the tab becomes visible after completing in the background", () => {
    setDocumentHidden(true);

    const { rerender } = renderHook(
      ({ isStreaming }) => useFavicon(isStreaming),
      { initialProps: { isStreaming: false } },
    );

    rerender({ isStreaming: true });
    rerender({ isStreaming: false });

    expect(getIconHref()).toBe(READY_ICON);

    setDocumentHidden(false);
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(getIconHref()).toBe(DEFAULT_ICON);
  });

  it("re-applies the processing favicon when streaming restarts after a background completion", () => {
    setDocumentHidden(true);

    const { rerender } = renderHook(
      ({ isStreaming }) => useFavicon(isStreaming),
      { initialProps: { isStreaming: false } },
    );

    rerender({ isStreaming: true });
    rerender({ isStreaming: false });

    expect(getIconHref()).toBe(READY_ICON);

    rerender({ isStreaming: true });

    expect(getIconHref()).toBe(PROCESSING_ICON);
  });
});
