// Fetch wrapper for calls that may need a login: adds the token, parses JSON, turns
// failures into ApiError and reports an expired session in one place.
// The browser calls /api/... and the Vite proxy forwards it to the backend (Part 0).
import { clearToken, getToken } from "../auth/tokenStorage";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let onSessionExpired = () => {};

/** AuthProvider registers a function that clears the user when a 401 arrives. */
export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler;
}

/** Pick a readable message out of FastAPI's error body. */
function messageFromBody(body) {
  if (typeof body?.detail === "string") return body.detail;
  return "Check the form and try again.";
}

/**
 * Call the backend and return the parsed JSON.
 * @param {string} path e.g. "/api/auth/me"
 * @param {{method?: string, body?: object}} [options]
 * @throws {ApiError} with the HTTP status (0 when the server cannot be reached)
 */
export async function apiRequest(path, { method = "GET", body } = {}) {
  const token = getToken();
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the server. Check your connection and try again.");
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // A 401 while holding a token means the session ended; a failed login has no token yet.
    if (response.status === 401 && token) {
      clearToken();
      onSessionExpired();
    }
    throw new ApiError(response.status, messageFromBody(data));
  }
  return data;
}
