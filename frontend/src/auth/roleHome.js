// Where each role lands after logging in.
const ROLE_HOME = { admin: "/admin", driver: "/driver" };

/** Return the home path for a role, or the login page for an unknown role. */
export function homePathForRole(role) {
  return ROLE_HOME[role] ?? "/login";
}
