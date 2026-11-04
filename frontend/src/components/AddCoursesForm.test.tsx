import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { addCourses } from "../api/courses";
import AddCoursesForm from "./AddCoursesForm";

vi.mock("../api/courses", () => ({ addCourses: vi.fn((courses: unknown[]) => Promise.resolve(courses)) }));

describe("AddCoursesForm", () => {
  it("adds several courses at once to the semester it was opened from", async () => {
    const onAdded = vi.fn();
    render(<AddCoursesForm level={200} semester={2} fixed onClose={vi.fn()} onAdded={onAdded} />);
    expect(screen.queryByLabelText("Level")).toBeNull();
    expect(screen.getByText("Add Level 200, Semester 2 courses")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Course 1 code"), { target: { value: "DCIT 201" } });
    fireEvent.change(screen.getByLabelText("Course 1 name"), { target: { value: "Data Structures" } });
    fireEvent.change(screen.getByLabelText("Course 2 code"), { target: { value: "DCIT 203" } });
    fireEvent.change(screen.getByLabelText("Course 2 name"), { target: { value: "Networks" } });
    fireEvent.click(screen.getByRole("button", { name: "Save 2 courses" }));

    await waitFor(() => expect(onAdded).toHaveBeenCalledWith(2, 0, 200));
    expect(addCourses).toHaveBeenCalledWith([
      { code: "DCIT 201", name: "Data Structures", level: 200, semester: 2 },
      { code: "DCIT 203", name: "Networks", level: 200, semester: 2 },
    ]);
  });

  it("lets the general Add courses button choose the level and semester", () => {
    render(<AddCoursesForm level={100} semester={1} onClose={vi.fn()} onAdded={vi.fn()} />);
    expect(screen.getByLabelText("Level")).toHaveValue("100");
    expect(screen.getByLabelText("Semester")).toHaveValue("1");
  });
});
