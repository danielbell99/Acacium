import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the scoped document inventory", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ documents: [], selected_report_page_count: 105 }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const response = await api.documents();

    expect(response.selected_report_page_count).toBe(105);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/documents",
      expect.any(Object),
    );
  });

  it("sends the reviewer rationale with a decision", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: "signal-1" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.reviewSignal("signal-1", "approved", "Primary source verified.");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/signals/signal-1/review",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          decision: "approved",
          reason: "Primary source verified.",
        }),
      }),
    );
  });
});
