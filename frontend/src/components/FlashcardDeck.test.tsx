import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AssessmentItem } from "../api/assessments";
import { reviewCard } from "../api/review";
import FlashcardDeck, { deal } from "./FlashcardDeck";

vi.mock("../api/review", () => ({ reviewCard: vi.fn(() => Promise.resolve()) }));

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

  it("moves through the deck and finishes at the end", () => {
    render(<FlashcardDeck items={cards(2)} />);
    fireEvent.click(screen.getByRole("button", { name: /Skip/ }));
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
    fireEvent.click(screen.getByRole("button", { name: /Skip/ }));
    fireEvent.click(screen.getByRole("button", { name: /Back/ }));
    expect(screen.getByText("Card 1")).toBeInTheDocument();
  });

  it("asks whether you knew a card once it is turned over, and schedules it", () => {
    vi.mocked(reviewCard).mockClear();
    render(<FlashcardDeck items={cards(2)} />);
    expect(screen.queryByRole("button", { name: /Got it/ })).toBeNull();

    fireEvent.click(card());
    fireEvent.click(screen.getByRole("button", { name: /Got it/ }));
    expect(reviewCard).toHaveBeenCalledTimes(1);
    expect(vi.mocked(reviewCard).mock.calls[0][1]).toBe(true);
    expect(screen.getByText("Card 2")).toBeInTheDocument();

    fireEvent.click(card());
    fireEvent.click(screen.getByRole("button", { name: /Still learning/ }));
    expect(vi.mocked(reviewCard).mock.calls[1][1]).toBe(false);
    expect(screen.getByText("Deck complete")).toBeInTheDocument();
    expect(screen.getByText(/You knew/)).toHaveTextContent("You knew 1 of 2");
  });
});
