import { apiGet } from './client.js';

/** Ask the backend whether it and its database are working. */
export function fetchHealth(signal) {
  return apiGet('/health', signal);
}
