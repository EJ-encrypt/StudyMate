import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CourseImport from "./CourseImport";

const readCourseList = vi.fn();
const addCourses = vi.fn();

vi.mock("../api/courses", () => ({
  readCourseList: (...args: unknown[]) => readCourseList(...args),
  addCourses: (...args: unknown[]) => addCourses(...args),
}));
vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ user: { level: 200, semester: 1 } }) }));

describe("Course import", () => {
  beforeEach(() => {
    readCourseList.mockReset().mockResolvedValue([
      { code: "MATH 223", name: "Calculus II", level: 200, semester: 1, already_added: false },
      { code: "MATH 224", name: "Linear Algebra", level: 200, semester: 2, already_added: false },
      { code: "STAT 201", name: "Probability", level: null, semester: null, already_added: false },
      { code: "CSCD 302", name: "Database Systems", level: 200, semester: 1, already_added: true },
    ]);
    addCourses.mockReset().mockImplementation(async (courses: unknown[]) => courses);
  });

  async function upload() {
    const { container } = render(<CourseImport onDone={onDone} onCancel={vi.fn()} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [new File(["x"], "slip.png", { type: "image/png" })] } });
    await screen.findByText(/Which of these are you studying/);
  }
  const onDone = vi.fn();

  it("pre-ticks the courses that fit this semester, and not ones already added", async () => {
    await upload();
    const box = (name: string) => screen.getByRole("checkbox", { name: new RegExp(name) });
    expect(box("Calculus II")).toHaveAttribute("aria-checked", "true");
    expect(box("Probability")).toHaveAttribute("aria-checked", "true");
    expect(box("Linear Algebra")).toHaveAttribute("aria-checked", "false");
    expect(box("Database Systems")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add 2 courses" })).toBeInTheDocument();
  });

  it("adds the ticked courses under the chosen level and semester", async () => {
    await upload();
    fireEvent.click(screen.getByRole("checkbox", { name: /Probability/ }));
    fireEvent.click(screen.getByRole("button", { name: "Add 1 course" }));

    await waitFor(() => expect(addCourses).toHaveBeenCalledTimes(1));
    expect(addCourses.mock.calls[0][0]).toEqual([{ code: "MATH 223", name: "Calculus II", level: 200, semester: 1 }]);
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(1));
  });
});
