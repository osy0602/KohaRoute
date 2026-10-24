import { Route } from "react-router-dom";
import RequireRole from "../auth/RequireRole";
import LoginPage from "../pages/LoginPage";
import StaffHomePlaceholder from "../pages/StaffHomePlaceholder";

/**
 * Login plus the two staff areas. Placed inside <Routes> in App.jsx so Part 0's Setup
 * check route is left untouched. Later parts add their screens under /admin and /driver.
 */
export const staffRoutes = (
  <>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/admin/*"
      element={
        <RequireRole role="admin">
          <StaffHomePlaceholder title="Admin dashboard" />
        </RequireRole>
      }
    />
    <Route
      path="/driver/*"
      element={
        <RequireRole role="driver">
          <StaffHomePlaceholder title="My route" />
        </RequireRole>
      }
    />
  </>
);
