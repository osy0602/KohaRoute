import { API_BASE, apiRequest } from './http';
import { getToken } from '../auth/tokenStorage';

// The NZ date helper now lives in ./health so Admin pages can share it.
export { getNzToday } from './health';

/** Load the logged-in driver's own saved routes for the selected day. */
export function getMyRoutes(pickupDate) {
  const query = new URLSearchParams();
  if (pickupDate) query.set('pickup_date', pickupDate);
  const suffix = query.size ? `?${query}` : '';
  return apiRequest(`/api/driver/routes${suffix}`);
}

/** Submit a one-way stop update to Completed or Missed. */
export function updateMyStop(routeId, bookingId, status, remark = '') {
  return apiRequest(`/api/driver/routes/${routeId}/stops/${bookingId}`, {
    method: 'PATCH',
    body: { status, remark },
  });
}

/** Fetch a private route photo through the authenticated assigned-driver endpoint. */
export async function fetchDriverPhoto(routeId, bookingId, photoId, signal) {
  const response = await fetch(
    `${API_BASE}/api/driver/routes/${routeId}/stops/${bookingId}/photos/${photoId}`,
    { headers: { Authorization: `Bearer ${getToken()}` }, signal },
  );
  if (!response.ok) throw new Error('Could not load this photo.');
  return URL.createObjectURL(await response.blob());
}
