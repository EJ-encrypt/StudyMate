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

const hidden = () => screen.queryAllByRole("button", { name: "Hidden card" });

describe("Concept Match", () => {
  beforeEach(() => {
    // With random() just under 1 the shuffle swaps nothing, so cards are dealt
    // in order: Deadlock, its clue, Paging, its clue.
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

  it("deals two face-down cards per concept", async () => {
    renderGame();
    await waitFor(() => expect(hidden()).toHaveLength(4));
  });

  it("keeps a matched pair face up", async () => {
    renderGame();
    await waitFor(() => expect(hidden()).toHaveLength(4));
    const [deadlock, deadlockClue] = hidden();

    fireEvent.click(deadlock);
    fireEvent.click(deadlockClue);

    expect(hidden()).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Deadlock" })).toBeDisabled();
  });

  it("turns a wrong pair back over and counts it as a mistake", async () => {
    renderGame();
    await waitFor(() => expect(hidden()).toHaveLength(4));
    const [deadlock, , paging] = hidden();

    fireEvent.click(deadlock);
    fireEvent.click(paging);
    expect(hidden()).toHaveLength(2);

    await waitFor(() => expect(hidden()).toHaveLength(4), { timeout: 2000 });
  });

  it("submits the round, with its mistakes, once every pair is found", async () => {
    renderGame();
    await waitFor(() => expect(hidden()).toHaveLength(4));
    const cards = hidden();

    fireEvent.click(cards[0]);
    fireEvent.click(cards[2]); // wrong
    await waitFor(() => expect(hidden()).toHaveLength(4), { timeout: 2000 });

    fireEvent.click(cards[0]);
    fireEvent.click(cards[1]);
    fireEvent.click(cards[2]);
    fireEvent.click(cards[3]);

    await waitFor(() => expect(submitConceptMatch).toHaveBeenCalledTimes(1));
    const [courseId, conceptIds, mistakes] = submitConceptMatch.mock.calls[0];
    expect(courseId).toBe("course-1");
    expect(conceptIds).toEqual(["c1", "c2"]);
    expect(mistakes).toBe(1);
    expect(await screen.findByText("New personal best!")).toBeInTheDocument();
  });
});
