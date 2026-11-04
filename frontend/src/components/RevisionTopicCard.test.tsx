import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { explainTopic, RevisionTopic } from "../api/coach";
import RevisionTopicCard from "./RevisionTopicCard";

vi.mock("../api/coach", async (original) => ({
  ...(await original<typeof import("../api/coach")>()),
  explainTopic: vi.fn(() =>
    Promise.resolve({ overview: "Both are about storing data without repeats.", links: { c2: "It is how 2NF is reached." } }),
  ),
}));

const topic: RevisionTopic = {
  title: "Normalisation",
  summary: "Removing redundancy from tables.",
  status: "weak",
  concepts: [
    { concept_id: "c1", name: "Normalisation", summary: "Removing redundancy.", score: 0.8, attempts: 4, correct: 3,
      status: "strong", last_seen_at: null,
      sources: [{ document_id: "d1", filename: "Week 2.pdf", location: "Page 3" }] },
    { concept_id: "c2", name: "Partial dependency", summary: "Depends on part of a key.", score: 0.2, attempts: 5,
      correct: 1, status: "weak", last_seen_at: null, sources: [] },
  ],
};

describe("RevisionTopicCard", () => {
  it("opens to show the concepts, their sources and how they tie together", async () => {
    render(
      <MemoryRouter>
        <ol>
          <RevisionTopicCard courseId="course-1" topic={topic} number={1} />
        </ol>
      </MemoryRouter>,
    );
    expect(screen.queryByText("Partial dependency")).toBeNull();

    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(screen.getByText("Partial dependency")).toBeInTheDocument();
    expect(screen.getByText(/Week 2\.pdf/)).toHaveTextContent("Week 2.pdf · Page 3");

    await waitFor(() => expect(screen.getByText("Both are about storing data without repeats.")).toBeInTheDocument());
    expect(screen.getByText("It is how 2NF is reached.")).toBeInTheDocument();
    expect(explainTopic).toHaveBeenCalledWith("course-1", ["c1", "c2"]);

    // Closing and opening again does not ask the AI a second time.
    fireEvent.click(screen.getByRole("button", { expanded: true }));
    fireEvent.click(screen.getByRole("button", { expanded: false }));
    expect(explainTopic).toHaveBeenCalledTimes(1);
  });
});
