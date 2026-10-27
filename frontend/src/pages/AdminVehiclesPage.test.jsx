import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom/vitest';
import AdminVehiclesPage from './AdminVehiclesPage';
import {
  createAdminVehicle,
  deactivateAdminVehicle,
  getAdminVehicles,
  updateAdminVehicle,
} from '../api/adminVehicles';

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ user: { full_name: 'Review Admin' }, logout: vi.fn() }),
}));
vi.mock('../api/adminVehicles', () => ({
  createAdminVehicle: vi.fn(),
  deactivateAdminVehicle: vi.fn(),
  getAdminVehicles: vi.fn(),
  updateAdminVehicle: vi.fn(),
}));

const activeVehicle = {
  id: 1,
  name: 'Demo Van',
  plate_number: 'KOHA01',
  capacity_kg: 600,
  capacity_litres: 3000,
  is_active: true,
};

function renderVehicles() {
  return render(
    <MemoryRouter>
      <AdminVehiclesPage />
    </MemoryRouter>,
  );
}

describe('AdminVehiclesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAdminVehicles.mockResolvedValue([activeVehicle]);
    createAdminVehicle.mockResolvedValue({ ...activeVehicle, id: 2 });
    updateAdminVehicle.mockResolvedValue({ ...activeVehicle, capacity_kg: 700 });
    deactivateAdminVehicle.mockResolvedValue({ ...activeVehicle, is_active: false });
  });

  it('lists vehicle name, plate, capacities, and active status', async () => {
    renderVehicles();
    expect(await screen.findByText('Demo Van')).toBeInTheDocument();
    expect(screen.getByText('KOHA01')).toBeInTheDocument();
    expect(screen.getByText('600')).toBeInTheDocument();
    expect(screen.getByText('3.00')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('blocks invalid values and creates a normalized vehicle', async () => {
    renderVehicles();
    fireEvent.click(await screen.findByRole('button', { name: 'Add vehicle' }));
    const dialog = screen.getByRole('dialog', { name: 'Add vehicle' });
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Vehicle name/ }), {
      target: { value: '  Community Van ' },
    });
    fireEvent.change(within(dialog).getByRole('textbox', { name: /Plate number/ }), {
      target: { value: 'koha03' },
    });
    fireEvent.change(within(dialog).getByRole('spinbutton', { name: /Capacity \(kg\)/ }), {
      target: { value: '500' },
    });
    fireEvent.change(within(dialog).getByRole('spinbutton', { name: /Capacity \(litres\)/ }), {
      target: { value: '2500' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add vehicle' }));

    await waitFor(() =>
      expect(createAdminVehicle).toHaveBeenCalledWith({
        name: 'Community Van',
        plate_number: 'KOHA03',
        capacity_kg: 500,
        capacity_litres: 2500,
      }),
    );
  });

  it('edits a vehicle and soft-deactivates without a delete action', async () => {
    renderVehicles();
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
    const editDialog = screen.getByRole('dialog', { name: 'Edit vehicle' });
    fireEvent.change(within(editDialog).getByRole('spinbutton', { name: /Capacity \(kg\)/ }), {
      target: { value: '700' },
    });
    fireEvent.click(within(editDialog).getByRole('button', { name: 'Save changes' }));
    await waitFor(() =>
      expect(updateAdminVehicle).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ capacity_kg: 700 }),
      ),
    );

    fireEvent.click(await screen.findByRole('button', { name: 'Deactivate' }));
    const confirmDialog = screen.getByRole('dialog', { name: 'Deactivate vehicle?' });
    fireEvent.click(within(confirmDialog).getByRole('button', { name: 'Deactivate' }));
    await waitFor(() => expect(deactivateAdminVehicle).toHaveBeenCalledWith(1));
  });
});
