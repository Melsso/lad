import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "../../src/services/api";

describe("api", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches the given path under the /api prefix", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api("/chat/messages?chat_id=1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/messages?chat_id=1",
      expect.objectContaining({
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ hello: "world" }), { status: 200 }),
        ),
    );

    const result = await api<{ hello: string }>("/chat/messages");

    expect(result).toEqual({ hello: "world" });
  });

  it("merges caller-provided headers with the default", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await api("/chat/messages", { headers: { "X-Custom": "1" } });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers).toEqual({
      "Content-Type": "application/json",
      "X-Custom": "1",
    });
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(null, { status: 404, statusText: "Not Found" }),
        ),
    );

    await expect(api("/chat/messages")).rejects.toThrow(/404/);
  });
});
