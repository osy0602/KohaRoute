import { apiRequest } from './http';

/** Load active drivers, vehicles, booking count, and replacement state for a date. */
export function getRoutePlanningOptions(pickupDate) {
  const query = new URLSearchParams({ pickup_date: pickupDate });
  return apiRequest(`/api/admin/routes/options?${query}`);
}

/** Read a previously saved route plan without calling ORS. */
export function getAdminRoutes(pickupDate) {
  const query = new URLSearchParams({ pickup_date: pickupDate });
  return apiRequest(`/api/admin/routes?${query}`);
}

/** Daily weight, volume and stop totals across every route on one date (US-08). */
export function getRouteDailyTotals(pickupDate) {
  const query = new URLSearchParams({ pickup_date: pickupDate });
  return apiRequest(`/api/admin/routes/totals?${query}`);
}

/** Generate or safely replace the route plan for one pickup date. */
export function generateAdminRoutes(payload) {
  return apiRequest('/api/admin/routes/generate', { method: 'POST', body: payload });
}
