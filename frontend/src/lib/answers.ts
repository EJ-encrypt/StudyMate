/**
 * Puts a typed answer in a form to compare: no accents, case, punctuation or
 * "a/an/the". Mirrors the server's marking closely enough for instant
 * feedback in the games; the server's verdict is final.
 */
export function normalizeAnswer(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .split(/\s+/)
    .filter((word) => word && !["a", "an", "the"].includes(word))
    .join(" ");
}
