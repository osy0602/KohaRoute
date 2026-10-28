import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiRequest, setSessionExpiredHandler } from "../api/http";
import { clearToken, getToken, saveToken } from "./tokenStorage";

const AuthContext = createContext(null);

/** Holds the logged-in user and restores the session from the saved token on load. */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isRestoring, setIsRestoring] = useState(Boolean(getToken()));

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));
    if (!getToken()) return;
    apiRequest("/api/auth/me")
      .then(setUser)
      .catch(clearToken) // expired or invalid token: fall back to the login page
      .finally(() => setIsRestoring(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const result = await apiRequest("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    saveToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const value = useMemo(
    () => ({ user, isRestoring, login, logout }),
    [user, isRestoring, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the current user and the login and logout actions. */
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
