// Keeps the access token in sessionStorage (cleared when the tab closes).
// Every call is wrapped in try/catch because the browser can block storage.
const TOKEN_KEY = 'koharoute.token';

/** Return the saved token, or null if there is none or storage is blocked. */
export function getToken() {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Save the token for this tab. */
export function saveToken(token) {
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Without storage the user simply logs in again after a reload.
  }
}

/** Forget the token (logout or expired session). */
export function clearToken() {
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Nothing to clear.
  }
}
