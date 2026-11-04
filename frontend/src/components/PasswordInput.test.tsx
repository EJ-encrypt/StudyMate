import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PasswordInput } from "./ui";

describe("PasswordInput", () => {
  it("hides what is typed until the eye button is pressed", () => {
    render(
      <label>
        Password
        <PasswordInput defaultValue="s3cret-pass" />
      </label>,
    );
    const field = screen.getByLabelText("Password");
    expect(field).toHaveAttribute("type", "password");

    fireEvent.click(screen.getByRole("button", { name: "Show password" }));
    expect(field).toHaveAttribute("type", "text");
    expect(field).toHaveValue("s3cret-pass");

    fireEvent.click(screen.getByRole("button", { name: "Hide password" }));
    expect(field).toHaveAttribute("type", "password");
  });
});
