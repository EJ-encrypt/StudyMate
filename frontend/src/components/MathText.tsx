import katex from "katex";
import { Fragment, useMemo } from "react";

/**
 * Text that may contain LaTeX between $...$ (inline) or $$...$$ (displayed),
 * as the AI writes it for maths, statistics and economics material.
 *
 * A dollar sign used as currency is left alone, by Pandoc's rule: inline
 * maths may not start or end with a space, nor be followed by a digit. So
 * "costs $5 and $10" stays text, while "$x^2$" renders.
 */
const MATH = /\$\$([\s\S]+?)\$\$|\$(?!\s)([^$\n]+?)(?<!\s)\$(?!\d)/g;

type Piece = { text: string } | { html: string; display: boolean };

function split(text: string): Piece[] {
  const pieces: Piece[] = [];
  let last = 0;
  for (const match of text.matchAll(MATH)) {
    const index = match.index ?? 0;
    const source = match[1] ?? match[2];
    const display = match[1] !== undefined;
    try {
      const html = katex.renderToString(source, { displayMode: display, throwOnError: true, strict: "ignore" });
      if (index > last) pieces.push({ text: text.slice(last, index) });
      pieces.push({ html, display });
      last = index + match[0].length;
    } catch {
      // Not valid LaTeX: leave it as written.
    }
  }
  if (last < text.length) pieces.push({ text: text.slice(last) });
  return pieces;
}

export default function MathText({ text, className }: { text: string; className?: string }) {
  const pieces = useMemo(() => (text.includes("$") ? split(text) : [{ text }]), [text]);
  return (
    <span className={className}>
      {pieces.map((piece, index) =>
        "text" in piece ? (
          <Fragment key={index}>{piece.text}</Fragment>
        ) : (
          <span
            key={index}
            className={piece.display ? "block" : undefined}
            // KaTeX output is generated markup from our own renderer, not user HTML.
            dangerouslySetInnerHTML={{ __html: piece.html }}
          />
        ),
      )}
    </span>
  );
}
