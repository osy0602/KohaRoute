import { apiRequest } from './http';

/** Get the server's New Zealand calendar date, the single source of "today" for the app. */
export async function getNzToday() {
  const health = await apiRequest('/api/health');
  return health.nz_today;
}
