import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { stopTour } from "../lib/tour";
import { NAV_ITEMS } from "./Nav";
import Tour, { TOUR_STEPS } from "./Tour";

const updatePreferences = vi.fn();
const refresh = vi.fn();
let user: Record<string, unknown> | null = null;

vi.mock("../api/auth", () => ({ updatePreferences: (...args: unknown[]) => updatePreferences(...args) }));
vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ user, refresh }) }));

function Page({ name }: { name: string }) {
  return <p>{name} page</p>;
}

function renderApp() {
  return render(
    <MemoryRouter initialEntries={["/courses"]}>
      <Tour />
      <a data-tour="nav-courses" href="/courses" style={{ display: "block" }}>
        My Courses
      </a>
      <Routes>
        {["/courses", "/study", "/coach", "/play", "/friends", "/schedule", "/settings"].map((path) => (
          <Route key={path} path={path} element={<Page name={path} />} />
        ))}
      </Routes>
    </MemoryRouter>,
  );
}

describe("Tour", () => {
  beforeEach(() => {
    act(() => stopTour());
    updatePreferences.mockReset().mockResolvedValue({});
    refresh.mockReset().mockResolvedValue(undefined);
  });

  it("visits every section, in the order of the tabs", () => {
    const firstVisit = NAV_ITEMS.map((item) => TOUR_STEPS.findIndex((step) => step.target === item.tour));
    firstVisit.forEach((index, i) => expect(index, `${NAV_ITEMS[i].label} is not in the tour`).toBeGreaterThan(-1));
    expect(firstVisit).toEqual([...firstVisit].sort((a, b) => a - b));
    for (const step of TOUR_STEPS) expect(step.body.length).toBeGreaterThan(40);
  });

  it("starts by itself for a new student and goes from page to page", async () => {
    user = { id: "u1", school: "UG", tutorial_seen: false };
    renderApp();
    expect(await screen.findByRole("dialog")).toHaveTextContent("Welcome to StudyMate");

    fireEvent.click(screen.getByRole("button", { name: /Show me/ }));
    expect(screen.getByRole("dialog")).toHaveTextContent("My Courses");

    // Through to the Study Engine step, which moves to its page.
    while (!screen.getByRole("dialog").textContent?.includes("Study Engine")) {
      fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    }
    expect(await screen.findByText("/study page")).toBeInTheDocument();
  });

  it("is marked seen when skipped, and does not start again", async () => {
    user = { id: "u1", school: "UG", tutorial_seen: false };
    renderApp();
    fireEvent.click(await screen.findByRole("button", { name: "Skip" }));
    await waitFor(() => expect(updatePreferences).toHaveBeenCalledWith({ tutorial_seen: true }));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("stays away for a student who has seen it", () => {
    user = { id: "u1", school: "UG", tutorial_seen: true };
    renderApp();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
