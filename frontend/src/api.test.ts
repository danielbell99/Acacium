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
});
