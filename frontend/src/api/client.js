const API_BASE_URL = '/api';

/** Error thrown when the backend answers with a failure status or cannot be reached. */
export class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/**
 * GET a JSON resource from the backend.
 *
 * @param {string} path - Path after /api, starting with a slash, e.g. "/health".
 * @param {AbortSignal} [signal] - Lets the caller cancel the request (e.g. on page change).
 * @returns {Promise<object>} The parsed JSON body.
 * @throws {ApiError} If the request fails or the status is not 2xx.
 */
export async function apiGet(path, signal) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      signal,
      headers: { Accept: 'application/json' },
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the backend');
  }
  if (!response.ok) {
    throw new ApiError(`Backend answered ${response.status}`, response.status);
  }
  return response.json();
}
