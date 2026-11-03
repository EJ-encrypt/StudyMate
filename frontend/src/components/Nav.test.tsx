import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NAV_ITEMS, Sidebar, TabBar } from "./Nav";

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

  it("offers the same sections in the phone tab bar", () => {
    render(
      <MemoryRouter>
        <TabBar />
      </MemoryRouter>,
    );
    const bar = screen.getByRole("navigation", { name: "Main" });
    expect(within(bar).getAllByRole("link")).toHaveLength(NAV_ITEMS.length);
    expect(within(bar).getByRole("link", { name: "Timetable" })).toHaveAttribute("href", "/schedule");
  });
});
