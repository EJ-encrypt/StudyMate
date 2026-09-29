import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";

function renderApp(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("shows the login form to a signed-out visitor", () => {
    renderApp("/login");
    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("hides the sidebar until someone is signed in", () => {
    renderApp("/login");
    expect(screen.queryByRole("link", { name: "My Courses" })).not.toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor to /login when hitting a protected page", async () => {
    renderApp("/courses");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });
});
