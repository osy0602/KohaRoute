import { apiRequest } from './http';
import { getToken } from '../auth/tokenStorage';

/** Load bookings matching the Admin status and pickup-date filters. */
export function getAdminBookings({ status = 'pending', pickupDate = '' } = {}) {
  const query = new URLSearchParams({ status });
  if (pickupDate) query.set('pickup_date', pickupDate);
  return apiRequest(`/api/admin/bookings?${query}`);
}

/** Load full details for an Admin review dialog. */
export function getAdminBooking(bookingId) {
  return apiRequest(`/api/admin/bookings/${bookingId}`);
}

/** Approve a Pending booking. */
export function approveAdminBooking(bookingId) {
  return apiRequest(`/api/admin/bookings/${bookingId}/approve`, { method: 'POST' });
}

/** Reject a Pending booking with the Admin's required reason. */
export function rejectAdminBooking(bookingId, reason) {
  return apiRequest(`/api/admin/bookings/${bookingId}/reject`, {
    method: 'POST',
    body: { reason },
  });
}

/** Reschedule an Approved or Missed booking. */
export function rescheduleAdminBooking(bookingId, pickupDate) {
  return apiRequest(`/api/admin/bookings/${bookingId}/reschedule`, {
    method: 'POST',
    body: { pickup_date: pickupDate },
  });
}

/** Fetch a private photo using the current staff session token. */
export async function fetchAdminPhoto(bookingId, photoId, signal) {
  const response = await fetch(`/api/admin/bookings/${bookingId}/photos/${photoId}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
    signal,
  });
  if (!response.ok) throw new Error('Could not load this photo.');
  return URL.createObjectURL(await response.blob());
}
