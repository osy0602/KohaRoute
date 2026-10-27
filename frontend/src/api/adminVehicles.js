import { apiRequest } from './http';

/** Load active and inactive vehicles for the Admin. */
export function getAdminVehicles() {
  return apiRequest('/api/admin/vehicles');
}

/** Create a new active vehicle. */
export function createAdminVehicle(vehicle) {
  return apiRequest('/api/admin/vehicles', { method: 'POST', body: vehicle });
}

/** Update a vehicle's editable details and capacities. */
export function updateAdminVehicle(vehicleId, vehicle) {
  return apiRequest(`/api/admin/vehicles/${vehicleId}`, { method: 'PUT', body: vehicle });
}

/** Deactivate a vehicle without deleting its database record. */
export function deactivateAdminVehicle(vehicleId) {
  return apiRequest(`/api/admin/vehicles/${vehicleId}/deactivate`, { method: 'PATCH' });
}
