import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { apiRequest } from '../api/http';
import TrackBooking from './TrackBooking';

vi.mock('../api/http', () => ({ apiRequest: vi.fn() }));

function renderTracker(entry = '/track') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <TrackBooking />
    </MemoryRouter>,
  );
}

describe('TrackBooking', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows public status, date, and area without private details', async () => {
    apiRequest.mockResolvedValue({
      status: 'scheduled',
      pickup_date: '2026-10-20',
      address_area: 'Westgate',
      rejection_reason: null,
      missed_message: null,
    });
    renderTracker();
    fireEvent.change(screen.getByLabelText('Booking reference'), {
      target: { value: 'KR-TRACK-EXAMPLE-01' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Check booking' }));

    expect(await screen.findByText('Scheduled')).toBeInTheDocument();
    expect(screen.getByText('Tuesday, 20 October 2026')).toBeInTheDocument();
    expect(screen.getByText('Westgate')).toBeInTheDocument();
    expect(screen.queryByText(/021 555/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Kohuhu Lane/)).not.toBeInTheDocument();
  });

  it('shows the rejection reason returned for a rejected booking', async () => {
    apiRequest.mockResolvedValue({
      status: 'rejected',
      pickup_date: '2026-10-20',
      address_area: 'Westgate',
      rejection_reason: 'The items cannot be accepted.',
      missed_message: null,
    });
    renderTracker('/track?reference=KR-REJECTED');
    fireEvent.click(screen.getByRole('button', { name: 'Check booking' }));
    expect(await screen.findByText('Reason: The items cannot be accepted.')).toBeInTheDocument();
    expect(apiRequest).toHaveBeenCalledWith('/api/bookings/track/KR-REJECTED');
  });

  it('shows the rescheduling message for a missed pickup', async () => {
    apiRequest.mockResolvedValue({
      status: 'missed',
      pickup_date: '2026-10-20',
      address_area: 'Westgate',
      rejection_reason: null,
      missed_message: 'The centre will contact you to reschedule this pickup.',
    });
    renderTracker();
    fireEvent.change(screen.getByLabelText('Booking reference'), {
      target: { value: 'KR-MISSED' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Check booking' }));
    expect(
      await screen.findByText('The centre will contact you to reschedule this pickup.'),
    ).toBeInTheDocument();
  });

  it('shows the agreed message for an unknown reference', async () => {
    apiRequest.mockRejectedValue({ status: 404, message: 'No booking found' });
    renderTracker();
    fireEvent.change(screen.getByLabelText('Booking reference'), {
      target: { value: 'UNKNOWN' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Check booking' }));
    expect(await screen.findByText('No booking found')).toBeInTheDocument();
  });
});
