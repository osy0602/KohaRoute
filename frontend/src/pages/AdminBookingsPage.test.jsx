import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import AdminBookingsPage from './AdminBookingsPage';
import {
  approveAdminBooking,
  getAdminBooking,
  getAdminBookings,
  rejectAdminBooking,
  rescheduleAdminBooking,
} from '../api/adminBookings';

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: { full_name: 'Review Admin' }, logout: vi.fn() }),
}));
vi.mock('../api/adminBookings', () => ({
  approveAdminBooking: vi.fn(),
  fetchAdminPhoto: vi.fn(),
  getAdminBooking: vi.fn(),
  getAdminBookings: vi.fn(),
  rejectAdminBooking: vi.fn(),
  rescheduleAdminBooking: vi.fn(),
}));

const pendingSummary = {
  id: 1,
  reference: 'KR-PENDING-01',
  donor_name: 'Aroha Donor',
  address_text: '11 Sample Road, Westgate, Auckland',
  pickup_date: '2026-10-20',
  category_names: ['Household items'],
  estimated_weight_kg: 30,
  estimated_volume_l: 120,
  status: 'pending',
  photos: [],
};

const pendingDetail = {
  ...pendingSummary,
  contact_number: '021 555 0101',
  latitude: -36.818826,
  longitude: 174.609864,
  description: 'Two boxes.',
  rejection_reason: null,
};

function renderAdmin() {
  return render(
    <MemoryRouter>
      <AdminBookingsPage />
    </MemoryRouter>,
  );
}

describe('AdminBookingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminBookings.mockResolvedValue([pendingSummary]);
    getAdminBooking.mockResolvedValue(pendingDetail);
    approveAdminBooking.mockResolvedValue({ ...pendingDetail, status: 'approved' });
    rejectAdminBooking.mockResolvedValue({
      ...pendingDetail,
      status: 'rejected',
      rejection_reason: 'Not suitable.',
    });
    rescheduleAdminBooking.mockResolvedValue({
      ...pendingDetail,
      status: 'approved',
      pickup_date: '2026-10-21',
    });
  });

  it('defaults to pending and displays the review summary fields', async () => {
    renderAdmin();
    expect(await screen.findByText('KR-PENDING-01')).toBeInTheDocument();
    expect(screen.getByText('Aroha Donor')).toBeInTheDocument();
    expect(screen.getByText('Household items')).toBeInTheDocument();
    expect(screen.getByText('30 kg · 120 L')).toBeInTheDocument();
    expect(getAdminBookings).toHaveBeenCalledWith({ status: 'pending', pickupDate: '' });
  });

  it('loads details and offers approve/reject only for a Pending booking', async () => {
    renderAdmin();
    fireEvent.click(await screen.findByRole('button', { name: 'Review' }));
    expect(await screen.findByText('Two boxes.')).toBeInTheDocument();
    expect(screen.getByText('021 555 0101')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reject' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reschedule' })).not.toBeInTheDocument();
  });

  it('requires a rejection reason before enabling confirmation', async () => {
    renderAdmin();
    fireEvent.click(await screen.findByRole('button', { name: 'Review' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Reject' }));
    const dialog = screen.getByRole('dialog', { name: 'Reject booking' });
    expect(within(dialog).getByRole('button', { name: 'Confirm rejection' })).toBeDisabled();
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Reason/ }), {
      target: { value: 'Not suitable.' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Confirm rejection' }));
    await waitFor(() => expect(rejectAdminBooking).toHaveBeenCalledWith(1, 'Not suitable.'));
  });

  it('offers rescheduling for Approved and Missed details', async () => {
    getAdminBookings.mockResolvedValue([{ ...pendingSummary, status: 'approved' }]);
    getAdminBooking.mockResolvedValue({ ...pendingDetail, status: 'approved' });
    renderAdmin();
    fireEvent.click(await screen.findByRole('button', { name: 'Review' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Reschedule' }));
    const dialog = screen.getByRole('dialog', { name: 'Reschedule pickup' });
    fireEvent.change(within(dialog).getByLabelText(/New pickup date/), {
      target: { value: '2026-10-21' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Save date' }));
    await waitFor(() => expect(rescheduleAdminBooking).toHaveBeenCalledWith(1, '2026-10-21'));
  });
});
