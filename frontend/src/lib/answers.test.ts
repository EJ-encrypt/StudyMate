import { describe, expect, it } from "vitest";

import { normalizeAnswer } from "./answers";

describe("normalizeAnswer", () => {
  it("ignores case, accents, punctuation and articles", () => {
    expect(normalizeAnswer("The Café, Normal-Form!")).toBe(normalizeAnswer("cafe normal form"));
    expect(normalizeAnswer("An  index")).toBe("index");
  });

  it("still tells different answers apart", () => {
    expect(normalizeAnswer("2NF")).not.toBe(normalizeAnswer("3NF"));
  });
});
