import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AssessmentItem } from "../api/assessments";
import FlashcardDeck, { deal } from "./FlashcardDeck";

function cards(count: number): AssessmentItem[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `card-${i}`,
    position: i + 1,
    kind: "flashcard" as const,
    question: `Term ${i}`,
    options: [],
    answer: `Definition ${i}`,
    explanation: null,
  }));
}

const card = () => screen.getByRole("button", { name: /Tap to/ });

describe("Flashcard deck", () => {
  it("mixes term-first and definition-first cards evenly", () => {
    const dealt = deal(cards(20));
    expect(dealt.filter((c) => c.termFirst)).toHaveLength(10);
    expect(new Set(dealt.map((c) => c.item.id)).size).toBe(20);
  });

  it("shows one card at a time and flips it on tap", () => {
    render(<FlashcardDeck items={cards(3)} />);
    expect(screen.getByText("Card 1")).toBeInTheDocument();
    expect(card()).toHaveAccessibleName(/Tap to reveal/);

    fireEvent.click(card());
    expect(card()).toHaveAccessibleName(/Tap to turn back/);
    expect(card().querySelector(".flip-card")?.className).toContain("is-flipped");
  });

  it("moves through the deck with Next and finishes at the end", () => {
    render(<FlashcardDeck items={cards(2)} />);
    fireEvent.click(card());
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("Card 2")).toBeInTheDocument();
    // The next card arrives face down.
    expect(card()).toHaveAccessibleName(/Tap to reveal/);

    fireEvent.click(screen.getByRole("button", { name: /Finish/ }));
    expect(screen.getByText("Deck complete")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Shuffle and go again/ }));
    expect(screen.getByText("Card 1")).toBeInTheDocument();
  });

  it("goes back a card, but not before the first", () => {
    render(<FlashcardDeck items={cards(2)} />);
    expect(screen.getByRole("button", { name: /Back/ })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    fireEvent.click(screen.getByRole("button", { name: /Back/ }));
    expect(screen.getByText("Card 1")).toBeInTheDocument();
  });
});
