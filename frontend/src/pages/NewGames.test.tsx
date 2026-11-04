import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// These play real-time games with real timers; on a slow machine running the
// whole suite at once, five seconds is not always enough.
vi.setConfig({ testTimeout: 20_000 });

import OddOneOut from "./OddOneOut";
import ThreeStrikes from "./ThreeStrikes";
import TrueFalse from "./TrueFalse";

const startRound = vi.fn();
const submitRound = vi.fn();

vi.mock("../api/games", () => ({
  startRound: (...args: unknown[]) => startRound(...args),
  submitRound: (...args: unknown[]) => submitRound(...args),
  startChallengeRound: vi.fn(),
  submitChallenge: vi.fn(),
}));
// The result card offers to challenge friends; not under test here.
vi.mock("../api/social", () => ({ getFriends: vi.fn(), createChallenges: vi.fn() }));

const BASE = { round_id: "r1", course_id: "c1", title: "CS1 · Systems", personal_best: null, challenge: null };
const RESULT = {
  game: "true_false", round_id: "r1", score: 100, correct: 1, total: 1, xp_awarded: 2,
  personal_best: 100, is_personal_best: true, new_badges: [], answers: [],
};

function renderAt(path: string, element: JSX.Element) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/play/:courseId/:game" element={element} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  startRound.mockReset();
  submitRound.mockReset().mockResolvedValue(RESULT);
});
afterEach(() => vi.useRealTimers());

describe("True or False Blitz", () => {
  it("judges each statement and submits what was said", async () => {
    startRound.mockResolvedValue({
      ...BASE,
      game: "true_false",
      seconds: 60,
      statements: [
        { key: "s1", subject: "Deadlock", claim: "Processes wait on each other forever.", is_true: true, explanation: "" },
        { key: "s2", subject: "Paging", claim: "Splits memory by function.", is_true: false, explanation: "" },
      ],
    });
    renderAt("/play/c1/blitz", <TrueFalse />);
    fireEvent.click(await screen.findByRole("button", { name: "Start" }));

    fireEvent.click(screen.getByRole("button", { name: /True/ }));
    // Feedback shows briefly, then the next statement.
    await screen.findByText("Splits memory by function.", {}, { timeout: 4000 });
    fireEvent.click(screen.getByRole("button", { name: /True/ }));

    await waitFor(() => expect(submitRound).toHaveBeenCalledTimes(1), { timeout: 4000 });
    const [, submission] = submitRound.mock.calls[0];
    expect(submission.answers.map((a: { key: string; response: string }) => [a.key, a.response])).toEqual([
      ["s1", "true"],
      ["s2", "true"],
    ]);
  });
});

describe("Odd One Out", () => {
  it("reveals the odd one and the shared theme", async () => {
    startRound.mockResolvedValue({
      ...BASE,
      game: "odd_one_out",
      puzzles: [
        {
          odd_id: "x",
          theme: "Normal forms",
          options: [
            { concept_id: "a", name: "1NF", summary: "Atomic values." },
            { concept_id: "x", name: "Deadlock", summary: "Waiting forever." },
            { concept_id: "b", name: "2NF", summary: "No partial dependencies." },
            { concept_id: "c", name: "3NF", summary: "No transitive dependencies." },
          ],
        },
      ],
    });
    renderAt("/play/c1/odd", <OddOneOut />);
    fireEvent.click(await screen.findByRole("button", { name: "Start" }));
    fireEvent.click(screen.getByRole("button", { name: "Deadlock" }));

    expect(screen.getByText(/Spot on/)).toHaveTextContent("all relate to Normal forms");
    fireEvent.click(screen.getByRole("button", { name: /See results/ }));
    await waitFor(() => expect(submitRound).toHaveBeenCalledTimes(1));
    expect(submitRound.mock.calls[0][1].answers[0]).toMatchObject({ key: "0", response: "x" });
  });
});

describe("Three Strikes", () => {
  it("ends the run on the third wrong answer", async () => {
    const questions = Array.from({ length: 6 }, (_, i) => ({
      item_id: `q${i}`, kind: "mcq", question: `Question ${i}?`, options: [`Right ${i}`, `Wrong ${i}`],
      answer: `Right ${i}`, explanation: "",
    }));
    startRound.mockResolvedValue({ ...BASE, game: "three_strikes", strikes: 3, questions });
    renderAt("/play/c1/strikes", <ThreeStrikes />);
    fireEvent.click(await screen.findByRole("button", { name: "Start" }));

    for (let i = 0; i < 3; i++) {
      const wrong = await screen.findByRole("button", { name: `Wrong ${i}` }, { timeout: 2000 });
      await act(async () => {
        fireEvent.click(wrong);
      });
    }
    await waitFor(() => expect(submitRound).toHaveBeenCalledTimes(1), { timeout: 3000 });
    expect(submitRound.mock.calls[0][1].answers).toHaveLength(3);
  });
});
