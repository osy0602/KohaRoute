import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import {
  createAdminVehicle,
  deactivateAdminVehicle,
  getAdminVehicles,
  updateAdminVehicle,
} from '../api/adminVehicles';

const EMPTY_VEHICLE = {
  name: '',
  plate_number: '',
  capacity_kg: '',
  capacity_litres: '',
};

function validateVehicle(form) {
  const errors = {};
  if (!form.name.trim()) errors.name = 'Enter a vehicle name.';
  if (!/^[a-z0-9]{1,6}$/i.test(form.plate_number.trim())) {
    errors.plate_number = 'Use 1 to 6 letters and numbers.';
  }
  for (const field of ['capacity_kg', 'capacity_litres']) {
    const value = Number(form[field]);
    if (!Number.isInteger(value) || value <= 0) errors[field] = 'Enter a positive whole number.';
  }
  return errors;
}

export default function AdminVehiclesPage() {
  const { user, logout } = useAuth();
  const [vehicles, setVehicles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState(null);
  const [deactivatingVehicle, setDeactivatingVehicle] = useState(null);
  const [form, setForm] = useState(EMPTY_VEHICLE);
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSaving, setIsSaving] = useState(false);

  async function loadVehicles() {
    setIsLoading(true);
    setError('');
    try {
      setVehicles(await getAdminVehicles());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadVehicles();
  }, []);

  function openCreateDialog() {
    setEditingVehicle(null);
    setForm(EMPTY_VEHICLE);
    setFieldErrors({});
    setDialogOpen(true);
  }

  function openEditDialog(vehicle) {
    setEditingVehicle(vehicle);
    setForm({
      name: vehicle.name,
      plate_number: vehicle.plate_number,
      capacity_kg: String(vehicle.capacity_kg),
      capacity_litres: String(vehicle.capacity_litres),
    });
    setFieldErrors({});
    setDialogOpen(true);
  }

  function closeDialog() {
    if (!isSaving) setDialogOpen(false);
  }

  async function submitVehicle(event) {
    event.preventDefault();
    const errors = validateVehicle(form);
    setFieldErrors(errors);
    setError('');
    if (Object.keys(errors).length) return;

    setIsSaving(true);
    const payload = {
      name: form.name.trim(),
      plate_number: form.plate_number.trim().toUpperCase(),
      capacity_kg: Number(form.capacity_kg),
      capacity_litres: Number(form.capacity_litres),
    };
    try {
      if (editingVehicle) await updateAdminVehicle(editingVehicle.id, payload);
      else await createAdminVehicle(payload);
      setDialogOpen(false);
      setNotice(editingVehicle ? 'Vehicle updated.' : 'Vehicle added.');
      await loadVehicles();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function confirmDeactivation() {
    if (!deactivatingVehicle) return;
    setIsSaving(true);
    setError('');
    try {
      await deactivateAdminVehicle(deactivatingVehicle.id);
      setDeactivatingVehicle(null);
      setNotice('Vehicle deactivated.');
      await loadVehicles();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Container maxWidth="lg" sx={{ py: { xs: 2, sm: 4 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        sx={{ mb: 3 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main">
            KohaRoute · Admin
          </Typography>
          <Typography component="h1" variant="h4">
            Vehicles
          </Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography color="text.secondary">{user?.full_name}</Typography>
          <Button variant="outlined" onClick={logout}>
            Log out
          </Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/admin" underline="hover">
          Booking review
        </Link>
        <Button variant="contained" onClick={openCreateDialog}>
          Add vehicle
        </Button>
      </Stack>
      {notice && (
        <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>
          {notice}
        </Alert>
      )}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer sx={{ overflowX: 'auto' }}>
        <Table size="small" aria-label="Admin vehicle list">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Plate</TableCell>
              <TableCell>Capacity (kg)</TableCell>
              <TableCell>Capacity (m³)</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6}>Loading vehicles…</TableCell>
              </TableRow>
            )}
            {!isLoading && vehicles.length === 0 && (
              <TableRow>
                <TableCell colSpan={6}>No vehicles have been added.</TableCell>
              </TableRow>
            )}
            {!isLoading &&
              vehicles.map((vehicle) => (
                <TableRow key={vehicle.id} hover>
                  <TableCell>{vehicle.name}</TableCell>
                  <TableCell sx={{ fontFamily: 'monospace' }}>{vehicle.plate_number}</TableCell>
                  <TableCell>{vehicle.capacity_kg}</TableCell>
                  <TableCell>{(vehicle.capacity_litres / 1000).toFixed(2)}</TableCell>
                  <TableCell>{vehicle.is_active ? 'Active' : 'Inactive'}</TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" onClick={() => openEditDialog(vehicle)}>
                        Edit
                      </Button>
                      {vehicle.is_active && (
                        <Button
                          size="small"
                          color="error"
                          onClick={() => setDeactivatingVehicle(vehicle)}
                        >
                          Deactivate
                        </Button>
                      )}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={closeDialog} fullWidth maxWidth="xs">
        <DialogTitle>{editingVehicle ? 'Edit vehicle' : 'Add vehicle'}</DialogTitle>
        <DialogContent>
          <Box
            component="form"
            id="vehicle-form"
            onSubmit={submitVehicle}
            sx={{ display: 'grid', gap: 2, pt: 1 }}
          >
            <TextField
              label="Vehicle name"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              error={Boolean(fieldErrors.name)}
              helperText={fieldErrors.name}
              required
              fullWidth
            />
            <TextField
              label="Plate number"
              value={form.plate_number}
              onChange={(event) =>
                setForm((current) => ({ ...current, plate_number: event.target.value }))
              }
              error={Boolean(fieldErrors.plate_number)}
              helperText={fieldErrors.plate_number || 'NZ plate: up to 6 letters and numbers'}
              inputProps={{ maxLength: 6, autoCapitalize: 'characters' }}
              required
              fullWidth
            />
            <TextField
              label="Capacity (kg)"
              type="number"
              value={form.capacity_kg}
              onChange={(event) =>
                setForm((current) => ({ ...current, capacity_kg: event.target.value }))
              }
              error={Boolean(fieldErrors.capacity_kg)}
              helperText={fieldErrors.capacity_kg}
              inputProps={{ min: 1, step: 1 }}
              required
              fullWidth
            />
            <TextField
              label="Capacity (litres)"
              type="number"
              value={form.capacity_litres}
              onChange={(event) =>
                setForm((current) => ({ ...current, capacity_litres: event.target.value }))
              }
              error={Boolean(fieldErrors.capacity_litres)}
              helperText={fieldErrors.capacity_litres || 'Stored as whole litres'}
              inputProps={{ min: 1, step: 1 }}
              required
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog} disabled={isSaving}>
            Cancel
          </Button>
          <Button type="submit" form="vehicle-form" variant="contained" disabled={isSaving}>
            {editingVehicle ? 'Save changes' : 'Add vehicle'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(deactivatingVehicle)}
        onClose={() => !isSaving && setDeactivatingVehicle(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Deactivate vehicle?</DialogTitle>
        <DialogContent>
          <Typography>
            {deactivatingVehicle?.name} will remain in the vehicle list as Inactive and will not be
            available for future routes.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeactivatingVehicle(null)} disabled={isSaving}>
            Cancel
          </Button>
          <Button color="error" onClick={confirmDeactivation} disabled={isSaving}>
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
