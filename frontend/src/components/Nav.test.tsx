import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { MobileHeader, NAV_ITEMS, Sidebar, TAB_ITEMS, TabBar } from "./Nav";

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "u1", full_name: "Ama Mensah", programme: "BSc IT", level: 200, semester: 1 },
    logout: vi.fn(),
  }),
}));
vi.mock("../api/profile", () => ({ getProgress: () => Promise.resolve({ xp: 1240 }) }));
vi.mock("../api/courses", () => ({
  listCourses: () =>
    Promise.resolve([
      { id: "c1", code: "DCIT 101", name: "Intro", level: 100, semester: 1 },
      { id: "c2", code: "DCIT 201", name: "Data", level: 200, semester: 1 },
    ]),
}));

describe("Navigation", () => {
  it("lists every section in the sidebar, each with an icon", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/play"]}>
        <Sidebar />
      </MemoryRouter>,
    );
    for (const item of NAV_ITEMS) {
      const link = screen.getByRole("link", { name: new RegExp(`^${item.label}`) });
      expect(link.querySelector("svg")).not.toBeNull();
    }
    expect(screen.getByRole("link", { name: "Arcade" }).className).toContain("text-gold");
    expect(container).toHaveTextContent("Ama Mensah");
  });

  it("puts the sections in study order, with Profile folded into Settings", () => {
    expect(NAV_ITEMS.map((item) => item.label)).toEqual([
      "My Courses",
      "Study Engine",
      "Coach",
      "Arcade",
      "Leaderboard",
      "Timetable",
      "Settings",
    ]);
  });

  it("shows the XP beside Leaderboard in the sidebar", async () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(await screen.findByRole("link", { name: /Leaderboard\s*1,240 XP/ })).toHaveAttribute("href", "/friends");
  });

  it("opens My Courses to every level, earlier ones included", async () => {
    render(
      <MemoryRouter initialEntries={["/courses"]}>
        <Sidebar />
      </MemoryRouter>,
    );
    const levels = await screen.findByRole("list", { name: "Levels" });
    expect(within(levels).getAllByRole("link").map((link) => link.getAttribute("href"))).toEqual([
      "/courses?level=100",
      "/courses?level=200",
    ]);
  });

  it("has only the Leaderboard, with the XP, in the phone header", async () => {
    render(
      <MemoryRouter>
        <MobileHeader />
      </MemoryRouter>,
    );
    const link = await screen.findByRole("link", { name: "Leaderboard, 1,240 XP" });
    expect(link).toHaveAttribute("href", "/friends");
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("puts Settings in the phone tab bar where Profile was", () => {
    render(
      <MemoryRouter>
        <TabBar />
      </MemoryRouter>,
    );
    const bar = screen.getByRole("navigation", { name: "Main" });
    const links = within(bar).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(TAB_ITEMS.map((item) => item.short));
    expect(links.map((link) => link.textContent)).toEqual(["Courses", "Study", "Coach", "Arcade", "Timetable", "Settings"]);
  });
});
