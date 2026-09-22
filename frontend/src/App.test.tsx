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
  it("shows the brand in the nav", () => {
    renderApp("/login");
    expect(screen.getByText("StudyMate AI")).toBeInTheDocument();
  });

  it("redirects an unauthenticated visitor to /login when hitting a protected page", async () => {
    renderApp("/upload");
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });
});
