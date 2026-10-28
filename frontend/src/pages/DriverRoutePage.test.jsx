import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import DriverRoutePage from './DriverRoutePage';
import { fetchDriverPhoto, getMyRoutes, getNzToday, updateMyStop } from '../api/driverRoutes';
import { ApiError } from '../api/http';

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: { full_name: 'Driver One' }, logout: vi.fn() }),
}));
vi.mock('../api/driverRoutes', () => ({
  fetchDriverPhoto: vi.fn(),
  getMyRoutes: vi.fn(),
  getNzToday: vi.fn(),
  updateMyStop: vi.fn(),
}));

global.URL.revokeObjectURL = vi.fn();

const route = {
  id: 1,
  pickup_date: '2026-10-20',
  status: 'planned',
  vehicle_name: 'Van',
  vehicle_plate_number: 'KOHA01',
  geometry: '',
  total_distance_m: 5000,
  total_duration_s: 1800,
  planned_weight_kg: 25,
  planned_volume_l: 100,
  stops: [
    {
      booking_id: 1,
      reference: 'KR-BOOK-001',
      sequence: 1,
      status: 'scheduled',
      address_text: '1 Sample Road, Auckland',
      latitude: -36.818826,
      longitude: 174.609864,
      donor_name: 'Donor One',
      contact_number: '021 555 0001',
      category_names: ['Household items'],
      estimated_weight_kg: 15,
      estimated_volume_l: 60,
      description: 'Two boxes.',
      remark: null,
      completed_at: null,
      updated_by_user_id: null,
      photos: [{ id: 1, content_type: 'image/jpeg' }],
    },
    {
      booking_id: 2,
      reference: 'KR-BOOK-002',
      sequence: 2,
      status: 'scheduled',
      address_text: '2 Sample Road, Auckland',
      latitude: -36.82,
      longitude: 174.61,
      donor_name: 'Donor Two',
      contact_number: '021 555 0002',
      category_names: ['Electronics'],
      estimated_weight_kg: 10,
      estimated_volume_l: 40,
      description: null,
      remark: null,
      completed_at: null,
      updated_by_user_id: null,
      photos: [],
    },
  ],
};

function renderDriver() {
  return render(
    <MemoryRouter>
      <DriverRoutePage />
    </MemoryRouter>,
  );
}

async function waitForRoute() {
  await waitFor(() => screen.getByText('Van · KOHA01 · 5.0 km · 30 min'));
}

describe('DriverRoutePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getNzToday.mockResolvedValue('2026-10-20');
    getMyRoutes.mockResolvedValue([route]);
    fetchDriverPhoto.mockResolvedValue('blob:mock-url');
  });

  it('shows route vehicle, distance and duration', async () => {
    renderDriver();
    await waitForRoute();
  });

  it('shows stops with address, donor and estimates', async () => {
    renderDriver();
    await waitForRoute();
    await screen.findByText('1 Sample Road, Auckland');
    await screen.findByText('Donor One');
    await screen.findByText('021 555 0001');
    await screen.findByText(/15 kg · 0.06 m³/);
    await screen.findByText('2 Sample Road, Auckland');
    await screen.findByText('Donor Two');
  });

  it('displays reference in stop detail', async () => {
    renderDriver();
    await waitForRoute();
    await screen.findByText(/KR-BOOK-001/);
    await screen.findByText(/KR-BOOK-002/);
  });

  it('shows photos for a stop', async () => {
    renderDriver();
    await waitForRoute();
    expect(screen.getByAltText('Donation item 1')).toBeInTheDocument();
  });

  it('shows no route message when none assigned', async () => {
    getMyRoutes.mockResolvedValue([]);
    renderDriver();
    await screen.findByText(/No route assigned for today/);
  });

  it('shows error with Try again button when route fails to load', async () => {
    getMyRoutes.mockRejectedValue(new Error('Could not load your route.'));
    renderDriver();
    await screen.findByText('Could not load your route.');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('shows exactly "No route assigned for today" with no trailing punctuation', async () => {
    getMyRoutes.mockResolvedValue([]);
    renderDriver();
    expect(await screen.findByText('No route assigned for today')).toBeInTheDocument();
  });

  it('puts the next scheduled stop at the top, then the rest in stop order', async () => {
    const firstDone = {
      ...route,
      stops: [{ ...route.stops[0], status: 'completed' }, route.stops[1]],
    };
    getMyRoutes.mockResolvedValue([firstDone]);
    renderDriver();
    await waitForRoute();
    const addresses = screen.getAllByRole('heading', { level: 2 }).map((node) => node.textContent);
    expect(addresses).toEqual(['2 Sample Road, Auckland', '1 Sample Road, Auckland']);
    expect(screen.getByText('Next stop')).toBeInTheDocument();
  });

  it('opens the stop address in Google Maps from the Navigate button', async () => {
    renderDriver();
    await waitForRoute();
    const [navigate] = screen.getAllByRole('link', { name: /Navigate with Google Maps/ });
    const href = navigate.getAttribute('href');
    expect(href.startsWith('https://www.google.com/maps/dir/?api=1&destination=')).toBe(true);
    expect(decodeURIComponent(href)).toContain('-36.818826,174.609864');
    expect(navigate).toHaveAttribute('target', '_blank');
  });

  it('offers a tap-to-call link for the donor contact number', async () => {
    renderDriver();
    await waitForRoute();
    expect(screen.getByRole('link', { name: '021 555 0001' })).toHaveAttribute('href', 'tel:0215550001');
  });

  it('shows a placeholder when a photo cannot be loaded', async () => {
    fetchDriverPhoto.mockRejectedValue(new Error('Could not load this photo.'));
    renderDriver();
    await waitForRoute();
    expect(await screen.findByRole('img', { name: /could not be loaded/ })).toBeInTheDocument();
  });

  it('does not fetch photos for stops that are still collapsed', async () => {
    const withSecondPhoto = {
      ...route,
      stops: [route.stops[0], { ...route.stops[1], photos: [{ id: 9, content_type: 'image/jpeg' }] }],
    };
    getMyRoutes.mockResolvedValue([withSecondPhoto]);
    renderDriver();
    await waitForRoute();
    await screen.findByAltText('Donation item 1');
    expect(fetchDriverPhoto).toHaveBeenCalledTimes(1);
    expect(fetchDriverPhoto.mock.calls[0][2]).toBe(1);
  });

  it('retries loading when Try again is pressed', async () => {
    getMyRoutes.mockRejectedValueOnce(new Error('Could not load your route.'));
    renderDriver();
    fireEvent.click(await screen.findByRole('button', { name: 'Try again' }));
    await waitForRoute();
    expect(getMyRoutes).toHaveBeenCalledTimes(2);
  });

  it('shows a friendly message, not a form hint, when the server fails', async () => {
    getMyRoutes.mockRejectedValue(new ApiError(500, 'Check the form and try again.'));
    renderDriver();
    expect(await screen.findByText('Could not load your route.')).toBeInTheDocument();
    expect(screen.queryByText(/Check the form/)).not.toBeInTheDocument();
  });

  it('keeps a failed stop update separate from the route load error', async () => {
    updateMyStop.mockRejectedValue(new Error('This stop has already been updated and cannot be changed.'));
    renderDriver();
    await waitForRoute();
    fireEvent.click(screen.getAllByRole('button', { name: 'Mark completed' })[0]);
    expect(await screen.findByText(/already been updated/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
    expect(screen.getByText('1 Sample Road, Auckland')).toBeInTheDocument();
  });

  it('ignores a cleared date field instead of leaving a stale route on screen', async () => {
    renderDriver();
    await waitForRoute();
    fireEvent.change(screen.getByLabelText('Route date'), { target: { value: '' } });
    expect(getMyRoutes).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Van · KOHA01 · 5.0 km · 30 min')).toBeInTheDocument();
  });

  it('says so when the route has no stops instead of showing only a map', async () => {
    getMyRoutes.mockResolvedValue([{ ...route, stops: [] }]);
    renderDriver();
    await waitForRoute();
    expect(screen.getByText(/No stops on this route/)).toBeInTheDocument();
    expect(screen.queryByText('Next stop')).not.toBeInTheDocument();
  });
});
