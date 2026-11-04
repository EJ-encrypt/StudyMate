import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NAV_ITEMS, Sidebar, TAB_ITEMS, TabBar } from "./Nav";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { full_name: "Ama Mensah", programme: "BSc IT", level: 400 },
    logout: vi.fn(),
  }),
}));

describe("Navigation", () => {
  it("lists every section in the sidebar, each with an icon", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/play"]}>
        <Sidebar />
      </MemoryRouter>,
    );
    for (const item of NAV_ITEMS) {
      const link = screen.getByRole("link", { name: item.label });
      expect(link.querySelector("svg")).not.toBeNull();
    }
    expect(screen.getByRole("link", { name: "Arcade" }).className).toContain("text-gold");
    expect(container).toHaveTextContent("Ama Mensah");
  });

  it("puts the sections in study order", () => {
    expect(NAV_ITEMS.map((item) => item.label)).toEqual([
      "My Courses",
      "Study Engine",
      "Coach",
      "Arcade",
      "Leaderboard",
      "Timetable",
      "Profile",
      "Settings",
    ]);
  });

  it("fits the main sections in the phone tab bar, in the same order", () => {
    render(
      <MemoryRouter>
        <TabBar />
      </MemoryRouter>,
    );
    const bar = screen.getByRole("navigation", { name: "Main" });
    const links = within(bar).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(TAB_ITEMS.map((item) => item.short));
    expect(links.map((link) => link.textContent)).toEqual(["Courses", "Study", "Coach", "Arcade", "Timetable", "Profile"]);
    expect(within(bar).getByRole("link", { name: "Timetable" })).toHaveAttribute("href", "/schedule");
  });
});
