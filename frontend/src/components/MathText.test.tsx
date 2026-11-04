import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MathText from "./MathText";

describe("MathText", () => {
  it("renders inline and displayed LaTeX", () => {
    const { container } = render(<MathText text="If $f(x) = x^2$ then $$f'(x) = 2x$$" />);
    expect(container.querySelectorAll(".katex")).toHaveLength(2);
    expect(container.querySelector(".katex-display")).not.toBeNull();
    expect(container).toHaveTextContent("If");
  });

  it("leaves prices alone", () => {
    const { container } = render(<MathText text="It costs $5 and $10 later" />);
    expect(container.querySelector(".katex")).toBeNull();
    expect(container).toHaveTextContent("It costs $5 and $10 later");
  });

  it("falls back to the raw text when the LaTeX is broken", () => {
    const { container } = render(<MathText text="Broken $\frac{1}{$ here" />);
    expect(container.querySelector(".katex")).toBeNull();
    expect(container).toHaveTextContent("Broken $\\frac{1}{$ here");
  });
});
