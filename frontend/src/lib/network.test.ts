import { AxiosError } from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";

import { errorMessage } from "../api/client";
import { isNetworkError, OFFLINE_MESSAGE } from "./network";

describe("network errors", () => {
  afterEach(() => vi.restoreAllMocks());

  it("recognises a lost connection however the browser words it", () => {
    expect(isNetworkError(new TypeError("Failed to fetch"))).toBe(true);
    expect(isNetworkError(new TypeError("Load failed"))).toBe(true);
    expect(isNetworkError(new AxiosError("Network Error", "ERR_NETWORK"))).toBe(true);
    expect(isNetworkError(new Error("Invalid login credentials"))).toBe(false);
  });

  it("treats everything as offline while the device says so", () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    expect(isNetworkError(new Error("anything"))).toBe(true);
  });

  it("explains a lost connection instead of the page's generic message", () => {
    expect(errorMessage(new AxiosError("Network Error", "ERR_NETWORK"), "Upload failed.")).toBe(OFFLINE_MESSAGE);
    const refused = new AxiosError("Bad", "ERR_BAD_REQUEST", undefined, undefined, {
      data: { detail: "That file is too large." },
      status: 400,
    } as never);
    expect(errorMessage(refused, "Upload failed.")).toBe("That file is too large.");
  });
});
