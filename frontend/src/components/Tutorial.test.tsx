import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { NAV_ITEMS } from "./Nav";
import Tutorial, { STEPS } from "./Tutorial";

const updatePreferences = vi.fn();
const refresh = vi.fn();
let user: Record<string, unknown> | null = null;

vi.mock("../api/auth", () => ({ updatePreferences: (...args: unknown[]) => updatePreferences(...args) }));
vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ user, refresh }) }));

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Tutorial />
    </MemoryRouter>,
  );
}

describe("Tutorial", () => {
  beforeEach(() => {
    updatePreferences.mockReset().mockResolvedValue({});
    refresh.mockReset().mockResolvedValue(undefined);
    user = { school: "University of Ghana", tutorial_seen: false };
  });

  it("opens on the home page for a student who has not seen it", () => {
    renderAt("/courses");
    expect(screen.getByRole("dialog")).toHaveTextContent("Welcome to StudyMate");
  });

  it("stays closed once seen, before onboarding, and on other pages", () => {
    user = { school: "University of Ghana", tutorial_seen: true };
    renderAt("/courses");
    expect(screen.queryByRole("dialog")).toBeNull();

    user = { school: null, tutorial_seen: false };
    renderAt("/courses");
    expect(screen.queryByRole("dialog")).toBeNull();

    user = { school: "University of Ghana", tutorial_seen: false };
    renderAt("/study");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("walks through every step and marks it seen at the end", async () => {
    renderAt("/courses");
    fireEvent.click(screen.getByRole("button", { name: /Show me/ }));
    for (let step = 1; step < STEPS.length - 1; step++) {
      expect(screen.getByRole("dialog")).toHaveTextContent(STEPS[step].title);
      fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    }
    fireEvent.click(screen.getByRole("button", { name: /Get started/ }));
    await waitFor(() => expect(updatePreferences).toHaveBeenCalledWith({ tutorial_seen: true }));
  });

  it("can be skipped", async () => {
    renderAt("/courses");
    fireEvent.click(screen.getByRole("button", { name: "Skip the tutorial" }));
    await waitFor(() => expect(updatePreferences).toHaveBeenCalledWith({ tutorial_seen: true }));
  });

  it("covers every tab, in the order the tabs appear", () => {
    const firstMention = NAV_ITEMS.map((item) =>
      STEPS.findIndex((step) => `${step.title} ${step.body}`.includes(item.label)),
    );
    firstMention.forEach((index, i) => expect(index, `${NAV_ITEMS[i].label} is not in the tutorial`).toBeGreaterThan(-1));
    expect(firstMention).toEqual([...firstMention].sort((a, b) => a - b));
  });
});
