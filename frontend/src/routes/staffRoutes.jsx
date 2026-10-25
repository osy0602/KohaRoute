import { Route } from 'react-router-dom';
import RequireRole from '../auth/RequireRole';
import LoginPage from '../pages/LoginPage';
import AdminBookingsPage from '../pages/AdminBookingsPage';
import StaffHomePlaceholder from '../pages/StaffHomePlaceholder';

/**
 * Login, Admin booking review, and the driver placeholder, each behind a role guard.
 */
export const staffRoutes = (
  <>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/admin/*"
      element={
        <RequireRole role="admin">
          <AdminBookingsPage />
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
