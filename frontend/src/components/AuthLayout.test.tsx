import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AuthLayout from "./AuthLayout";

vi.mock("../context/AuthContext", () => ({ useAuth: () => ({ isConfigured: true }) }));

describe("AuthLayout", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows the form while online", () => {
    render(
      <AuthLayout title="Log in">
        <p>the form</p>
      </AuthLayout>,
    );
    expect(screen.getByText("the form")).toBeInTheDocument();
  });

  it("shows an offline page instead of the form with no connection", () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    render(
      <AuthLayout title="Log in">
        <p>the form</p>
      </AuthLayout>,
    );
    expect(screen.queryByText("the form")).toBeNull();
    expect(screen.getByRole("alert")).toHaveTextContent("You're offline");
    expect(screen.getByRole("button", { name: /Try again/ })).toBeInTheDocument();
  });
});
