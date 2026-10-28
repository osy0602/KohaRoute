import { Box, CircularProgress } from "@mui/material";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { homePathForRole } from "./roleHome";

/**
 * Route guard for convenience only: the backend role check is the real protection.
 * Not logged in goes to the login page; the wrong role goes to that user's own home.
 */
export default function RequireRole({ role, children }) {
  const { user, isRestoring } = useAuth();
  const location = useLocation();

  if (isRestoring) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", minHeight: "60vh" }}>
        <CircularProgress aria-label="Loading" />
      </Box>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (user.role !== role) return <Navigate to={homePathForRole(user.role)} replace />;
  return children;
}
