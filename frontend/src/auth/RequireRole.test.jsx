// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import RequireRole from "./RequireRole";

const mockAuth = { user: null, isRestoring: false };
vi.mock("./AuthContext", () => ({ useAuth: () => mockAuth }));

/** Render an Admin-only page at /admin with login and driver pages beside it. */
function renderGuard(requiredRole) {
  return render(
    <MemoryRouter initialEntries={["/admin"]}>
      <Routes>
        <Route path="/login" element={<p>Login page</p>} />
        <Route path="/driver" element={<p>Driver home</p>} />
        <Route
          path="/admin"
          element={
            <RequireRole role={requiredRole}>
              <p>Admin secret</p>
            </RequireRole>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireRole", () => {
  it("sends a visitor who is not logged in to the login page", () => {
    Object.assign(mockAuth, { user: null, isRestoring: false });
    renderGuard("admin");
    expect(screen.getByText("Login page")).toBeInTheDocument();
  });

  it("sends a driver away from an Admin page to the driver home", () => {
    Object.assign(mockAuth, { user: { role: "driver" }, isRestoring: false });
    renderGuard("admin");
    expect(screen.getByText("Driver home")).toBeInTheDocument();
    expect(screen.queryByText("Admin secret")).not.toBeInTheDocument();
  });

  it("shows the page to the right role", () => {
    Object.assign(mockAuth, { user: { role: "admin" }, isRestoring: false });
    renderGuard("admin");
    expect(screen.getByText("Admin secret")).toBeInTheDocument();
  });
});
