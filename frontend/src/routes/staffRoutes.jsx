import { Suspense, lazy } from 'react';
import { Route } from 'react-router-dom';
import RequireRole from '../auth/RequireRole';
import LoginPage from '../pages/LoginPage';
import AdminBookingsPage from '../pages/AdminBookingsPage';
import AdminVehiclesPage from '../pages/AdminVehiclesPage';
import StaffHomePlaceholder from '../pages/StaffHomePlaceholder';

const AdminRoutesPage = lazy(() => import('../pages/AdminRoutesPage'));
const DriverRoutePage = lazy(() => import('../pages/DriverRoutePage'));

/**
 * Login, Admin booking review, and the driver placeholder, each behind a role guard.
 */
export const staffRoutes = (
  <>
    <Route path="/login" element={<LoginPage />} />
    <Route
      path="/admin/vehicles"
      element={
        <RequireRole role="admin">
          <AdminVehiclesPage />
        </RequireRole>
      }
    />
    <Route
      path="/admin/routes"
      element={
        <RequireRole role="admin">
          <Suspense fallback={<p>Loading route planner…</p>}>
            <AdminRoutesPage />
          </Suspense>
        </RequireRole>
      }
    />
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
          <Suspense fallback={<p>Loading your route…</p>}>
            <DriverRoutePage />
          </Suspense>
        </RequireRole>
      }
    />
  </>
);
