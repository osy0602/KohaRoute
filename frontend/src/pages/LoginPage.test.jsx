// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import LoginPage from "./LoginPage";

const login = vi.fn();
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: null, login }) }));

/** Render the login page inside a router. */
function renderPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    login.mockReset();
  });

  it("blocks empty fields with a message and does not call the server", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(screen.getByText("Enter your email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("shows the server's message when the login fails", async () => {
    login.mockRejectedValue(new Error("Invalid email or password"));
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@koha.nz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled());
  });
});
