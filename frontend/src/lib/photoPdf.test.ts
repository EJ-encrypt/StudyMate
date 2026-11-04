// @vitest-environment node
import { describe, expect, it } from "vitest";

import { buildPdf } from "./photoPdf";

describe("buildPdf", () => {
  it("writes one page per photo, with a cross-reference table that points at each object", async () => {
    const fakeJpeg = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);
    const blob = buildPdf([
      { jpeg: fakeJpeg, width: 300, height: 400 },
      { jpeg: fakeJpeg, width: 500, height: 250 },
    ]);
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const text = new TextDecoder("latin1").decode(bytes);

    expect(text.startsWith("%PDF-1.4")).toBe(true);
    expect(text).toContain("/Count 2");
    expect(text.match(/\/Type \/Page /g)).toHaveLength(2);

    // Readers find objects by byte offset; a wrong one makes the file "damaged".
    const xrefAt = Number(text.match(/startxref\n(\d+)/)![1]);
    expect(text.slice(xrefAt, xrefAt + 4)).toBe("xref");
    const entries = text.slice(xrefAt).split("\n").slice(3, 3 + 8);
    entries.forEach((entry, index) => {
      const offset = Number(entry.slice(0, 10));
      const header = `${index + 1} 0 obj\n`;
      expect(text.slice(offset, offset + header.length)).toBe(header);
    });
  });
});
