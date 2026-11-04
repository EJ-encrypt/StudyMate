import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ConceptMatch from "./ConceptMatch";

const submitConceptMatch = vi.fn();

vi.mock("../api/games", () => ({
  startConceptMatch: vi.fn(async () => ({
    course_id: "course-1",
    personal_best: null,
    pairs: [
      { concept_id: "c1", name: "Deadlock", clue: "Processes each wait on another forever." },
      { concept_id: "c2", name: "Paging", clue: "Memory split into fixed-size blocks." },
    ],
  })),
  submitConceptMatch: (...args: unknown[]) => submitConceptMatch(...args),
}));

function renderGame() {
  return render(
    <MemoryRouter initialEntries={["/play/course-1/match"]}>
      <Routes>
        <Route path="/play/:courseId/match" element={<ConceptMatch />} />
      </Routes>
    </MemoryRouter>,
  );
}

const concept = (name: string) => screen.getByRole("button", { name: new RegExp(`^Concept: ${name}`) });
const meaning = (start: string) => screen.getByRole("button", { name: new RegExp(`^Meaning: ${start}`) });

describe("Concept Match", () => {
  beforeEach(() => {
    vi.spyOn(Math, "random").mockReturnValue(0.9999);
    submitConceptMatch.mockReset();
    submitConceptMatch.mockResolvedValue({
      game: "concept_match",
      score: 350,
      correct: 2,
      total: 2,
      xp_awarded: 9,
      personal_best: 350,
      is_personal_best: true,
      new_badges: [],
      answers: [],
    });
  });

  afterEach(() => vi.restoreAllMocks());

  it("lays concepts and meanings out in two columns", async () => {
    renderGame();
    await screen.findByRole("region", { name: "Concepts" });
    expect(screen.getAllByRole("button", { name: /^Concept:/ })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /^Meaning:/ })).toHaveLength(2);
  });

  it("highlights a picked card, and locks a correct pair in green", async () => {
    renderGame();
    await screen.findByRole("region", { name: "Concepts" });

    fireEvent.click(concept("Deadlock"));
    expect(concept("Deadlock")).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(meaning("Processes"));
    expect(concept("Deadlock")).toBeDisabled();
    expect(meaning("Processes")).toBeDisabled();
    expect(concept("Deadlock").className).toContain("green");
  });

  it("shows a wrong pair in red, then resets it and counts a mistake", async () => {
    renderGame();
    await screen.findByRole("region", { name: "Concepts" });

    fireEvent.click(concept("Deadlock"));
    fireEvent.click(meaning("Memory"));
    expect(concept("Deadlock").className).toContain("red");
    expect(meaning("Memory").className).toContain("red");

    await waitFor(() => expect(concept("Deadlock").className).not.toContain("red"), { timeout: 2000 });
    expect(concept("Deadlock")).not.toBeDisabled();
    expect(concept("Deadlock")).toHaveAttribute("aria-pressed", "false");
  });

  it("submits the round, with its mistakes, once every pair is found", async () => {
    renderGame();
    await screen.findByRole("region", { name: "Concepts" });

    fireEvent.click(concept("Deadlock"));
    fireEvent.click(meaning("Memory")); // wrong
    await waitFor(() => expect(concept("Deadlock").className).not.toContain("red"), { timeout: 2000 });

    // Either side can go first.
    fireEvent.click(meaning("Processes"));
    fireEvent.click(concept("Deadlock"));
    fireEvent.click(concept("Paging"));
    fireEvent.click(meaning("Memory"));

    await waitFor(() => expect(submitConceptMatch).toHaveBeenCalledTimes(1));
    const [courseId, conceptIds, mistakes] = submitConceptMatch.mock.calls[0];
    expect(courseId).toBe("course-1");
    expect(conceptIds).toEqual(["c1", "c2"]);
    expect(mistakes).toBe(1);
    expect(await screen.findByText("New personal best!")).toBeInTheDocument();
  });
});
