import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { apiRequest } from '../api/http';
import BookPickup from './BookPickup';

vi.mock('../api/http', () => ({ apiRequest: vi.fn() }));

const options = {
  pickup_dates: ['2026-10-16'],
  earliest_pickup_date: '2026-10-16',
  latest_pickup_date: '2026-10-16',
  categories: [{ id: 1, name: 'Clothing and textiles' }],
  size_presets: [
    {
      key: 'small',
      label: 'Small',
      description: 'A shopping bag or small box',
      weight_kg: 5,
      volume_l: 20,
    },
    {
      key: 'medium',
      label: 'Medium',
      description: 'A standard moving box or a large bag',
      weight_kg: 15,
      volume_l: 60,
    },
  ],
  max_quantity: 10,
  min_photos: 1,
  max_photos: 3,
  max_photo_size_bytes: 5 * 1024 * 1024,
  description_max_chars: 300,
};

function renderBooking() {
  return render(
    <MemoryRouter>
      <BookPickup />
    </MemoryRouter>,
  );
}

describe('BookPickup', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiRequest.mockImplementation((path) => {
      if (path === '/api/bookings/options') return Promise.resolve(options);
      if (path.startsWith('/api/bookings/address-suggestions')) {
        return Promise.resolve([{ label: '1 Sample Road, Auckland', token: 'signed-address' }]);
      }
      if (path === '/api/bookings') {
        return Promise.resolve({
          reference: 'RANDOM-REFERENCE',
          pickup_date: '2026-10-16',
          status: 'pending',
          estimated_weight_kg: 30,
          estimated_volume_l: 120,
        });
      }
      return Promise.reject(new Error(`Unexpected API request: ${path}`));
    });
  });

  it('loads available categories and shows estimates from the preset and quantity', async () => {
    renderBooking();
    expect(await screen.findByText('Clothing and textiles')).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Donation size' }));
    fireEvent.click(await screen.findByRole('option', { name: /Medium/ }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Quantity' }), {
      target: { value: '3' },
    });

    expect(screen.getByText(/Estimated load: 45 kg · 0.18 m³/)).toBeInTheDocument();
  });

  it('blocks an incomplete request without calling the booking endpoint', async () => {
    renderBooking();
    fireEvent.click(await screen.findByRole('button', { name: 'Submit pickup request' }));

    expect(await screen.findByText('Enter your name.')).toBeInTheDocument();
    expect(screen.getByText('Choose at least one category.')).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalledWith('/api/bookings', expect.anything());
  });

  it('submits multipart donor details and shows the unguessable reference', async () => {
    renderBooking();
    fireEvent.change(await screen.findByRole('textbox', { name: /Your name/ }), {
      target: { value: 'Aroha Donor' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: /Contact number/ }), {
      target: { value: '021 555 0101' },
    });
    fireEvent.change(screen.getByRole('textbox', { name: /Auckland pickup address/ }), {
      target: { value: 'Sample Road' },
    });
    expect(await screen.findByRole('button', { name: '1 Sample Road, Auckland' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '1 Sample Road, Auckland' }));

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Pickup date' }));
    fireEvent.click(await screen.findByRole('option', { name: /Friday, 16 October/ }));
    fireEvent.click(screen.getByLabelText('Clothing and textiles'));
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Donation size' }));
    fireEvent.click(await screen.findByRole('option', { name: /Medium/ }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Quantity' }), {
      target: { value: '2' },
    });
    const photo = new File(['small test image'], 'donation.png', { type: 'image/png' });
    fireEvent.change(screen.getByLabelText('Choose photos'), { target: { files: [photo] } });
    fireEvent.click(screen.getByRole('button', { name: 'Submit pickup request' }));

    expect(await screen.findByText('RANDOM-REFERENCE')).toBeInTheDocument();
    await waitFor(() => expect(apiRequest).toHaveBeenCalledWith(
      '/api/bookings',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
    ));
    const submission = apiRequest.mock.calls.find(([path]) => path === '/api/bookings')[1];
    expect(submission.body.get('address_token')).toBe('signed-address');
    expect(submission.body.get('photos')).toBe(photo);
    expect(submission.body.get('category_ids')).toBe('1');
  });
});
