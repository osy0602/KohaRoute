import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  Link,
  MenuItem,
  Select,
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
import { getToken } from '../auth/tokenStorage';
import { useAuth } from '../auth/AuthContext';
import {
  approveAdminBooking,
  fetchAdminPhoto,
  getAdminBooking,
  getAdminBookings,
  rejectAdminBooking,
  rescheduleAdminBooking,
} from '../api/adminBookings';

const STATUS_OPTIONS = ['pending', 'approved', 'rejected', 'scheduled', 'completed', 'missed'];

function statusLabel(status) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-NZ', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`));
}

function PrivatePhoto({ bookingId, photo, index, large = false }) {
  const [imageUrl, setImageUrl] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    let currentUrl = '';
    fetchAdminPhoto(bookingId, photo.id, controller.signal)
      .then((url) => {
        currentUrl = url;
        setImageUrl(url);
      })
      .catch(() => setImageUrl(''));
    return () => {
      controller.abort();
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [bookingId, photo.id]);

  if (!imageUrl) return null;
  return (
    <Box
      component="img"
      src={imageUrl}
      alt={`Donation photo ${index + 1}`}
      sx={{
        width: large ? 220 : 64,
        height: large ? 160 : 64,
        objectFit: 'cover',
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 0.5,
      }}
    />
  );
}

function PhotoSet({ bookingId, photos = [], large = false }) {
  if (!photos.length) return <Typography color="text.secondary">No photos attached</Typography>;
  return (
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
      {photos.map((photo, index) => (
        <PrivatePhoto
          key={photo.id}
          bookingId={bookingId}
          photo={photo}
          index={index}
          large={large}
        />
      ))}
    </Stack>
  );
}

function BookingMap({ latitude, longitude }) {
  const margin = 0.01;
  const bounds = [
    longitude - margin,
    latitude - margin,
    longitude + margin,
    latitude + margin,
  ].join(',');
  const mapUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bounds}&layer=mapnik&marker=${latitude},${longitude}`;
  return (
    <Box
      component="iframe"
      title="Booking location map"
      src={mapUrl}
      loading="lazy"
      sx={{ width: '100%', height: 280, border: 0, display: 'block' }}
    />
  );
}

export default function AdminBookingsPage() {
  const { user, logout } = useAuth();
  const [statusFilter, setStatusFilter] = useState('pending');
  const [pickupDate, setPickupDate] = useState('');
  const [bookings, setBookings] = useState([]);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [newPickupDate, setNewPickupDate] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError('');
    getAdminBookings({ status: statusFilter, pickupDate })
      .then((result) => {
        if (active) setBookings(result);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [statusFilter, pickupDate, refreshKey]);

  async function openDetails(bookingId) {
    setError('');
    try {
      setSelectedBooking(await getAdminBooking(bookingId));
    } catch (requestError) {
      setError(requestError.message);
    }
  }

  async function updateBooking(action, successMessage) {
    if (!selectedBooking) return;
    setIsSaving(true);
    setError('');
    try {
      const updated = await action(selectedBooking.id);
      setSelectedBooking(updated);
      setNotice(successMessage);
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function submitRejection() {
    if (!selectedBooking || !rejectReason.trim()) return;
    setIsSaving(true);
    setError('');
    try {
      const updated = await rejectAdminBooking(selectedBooking.id, rejectReason.trim());
      setSelectedBooking(updated);
      setRejectOpen(false);
      setRejectReason('');
      setNotice('Booking rejected.');
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  async function submitReschedule() {
    if (!selectedBooking || !newPickupDate) return;
    setIsSaving(true);
    setError('');
    try {
      const updated = await rescheduleAdminBooking(selectedBooking.id, newPickupDate);
      setSelectedBooking(updated);
      setRescheduleOpen(false);
      setNewPickupDate('');
      setNotice('Pickup rescheduled.');
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  function closeDetail() {
    setSelectedBooking(null);
    setError('');
  }

  return (
    <Container maxWidth="xl" sx={{ py: { xs: 2, sm: 4 } }}>
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
            Booking review
          </Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography color="text.secondary">{user?.full_name}</Typography>
          <Button variant="outlined" onClick={logout}>
            Log out
          </Button>
        </Stack>
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

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <FormControl sx={{ minWidth: 190 }}>
          <InputLabel id="booking-status-filter-label">Status</InputLabel>
          <Select
            labelId="booking-status-filter-label"
            label="Status"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <MenuItem value="pending">Pending</MenuItem>
            <MenuItem value="all">All statuses</MenuItem>
            {STATUS_OPTIONS.filter((value) => value !== 'pending').map((value) => (
              <MenuItem key={value} value={value}>
                {statusLabel(value)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          label="Pickup date"
          type="date"
          value={pickupDate}
          onChange={(event) => setPickupDate(event.target.value)}
          InputLabelProps={{ shrink: true }}
          sx={{ minWidth: 190 }}
        />
        {pickupDate && <Button onClick={() => setPickupDate('')}>Clear date</Button>}
      </Stack>

      <TableContainer sx={{ overflowX: 'auto' }}>
        <Table size="small" aria-label="Booking review list">
          <TableHead>
            <TableRow>
              <TableCell>Reference</TableCell>
              <TableCell>Donor</TableCell>
              <TableCell>Address</TableCell>
              <TableCell>Categories</TableCell>
              <TableCell>Estimated load</TableCell>
              <TableCell>Pickup date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Photos</TableCell>
              <TableCell align="right">Details</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={9}>Loading bookings…</TableCell>
              </TableRow>
            )}
            {!isLoading && bookings.length === 0 && (
              <TableRow>
                <TableCell colSpan={9}>No bookings match these filters.</TableCell>
              </TableRow>
            )}
            {!isLoading &&
              bookings.map((booking) => (
                <TableRow key={booking.id} hover>
                  <TableCell sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
                    {booking.reference}
                  </TableCell>
                  <TableCell>{booking.donor_name}</TableCell>
                  <TableCell sx={{ minWidth: 180 }}>{booking.address_text}</TableCell>
                  <TableCell>{booking.category_names.join(', ')}</TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {booking.estimated_weight_kg} kg · {booking.estimated_volume_l} L
                  </TableCell>
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {formatDate(booking.pickup_date)}
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={statusLabel(booking.status)} />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      {booking.photos.slice(0, 3).map((photo, index) => (
                        <PrivatePhoto
                          key={photo.id}
                          bookingId={booking.id}
                          photo={photo}
                          index={index}
                        />
                      ))}
                    </Stack>
                  </TableCell>
                  <TableCell align="right">
                    <Button size="small" onClick={() => openDetails(booking.id)}>
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(selectedBooking)} onClose={closeDetail} fullWidth maxWidth="md">
        {selectedBooking && (
          <>
            <DialogTitle>
              <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
                <Box>
                  <Typography variant="overline">{selectedBooking.reference}</Typography>
                  <Typography component="h2" variant="h5">
                    {selectedBooking.donor_name}
                  </Typography>
                </Box>
                <Chip label={statusLabel(selectedBooking.status)} />
              </Stack>
            </DialogTitle>
            <DialogContent dividers>
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle2">Pickup</Typography>
                  <Typography>{selectedBooking.address_text}</Typography>
                  <Typography>{formatDate(selectedBooking.pickup_date)}</Typography>
                  <Typography>{selectedBooking.contact_number}</Typography>
                </Box>
                <Box>
                  <Typography variant="subtitle2">Items</Typography>
                  <Typography>{selectedBooking.category_names.join(', ')}</Typography>
                  <Typography>
                    {selectedBooking.estimated_weight_kg} kg · {selectedBooking.estimated_volume_l}{' '}
                    L estimated
                  </Typography>
                  <Typography>
                    Size: {selectedBooking.size} · Quantity: {selectedBooking.quantity}
                  </Typography>
                  <Typography sx={{ whiteSpace: 'pre-wrap' }}>
                    {selectedBooking.description || 'No description provided.'}
                  </Typography>
                </Box>
                {selectedBooking.rejection_reason && (
                  <Alert severity="warning">
                    Rejection reason: {selectedBooking.rejection_reason}
                  </Alert>
                )}
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Photos
                  </Typography>
                  <PhotoSet bookingId={selectedBooking.id} photos={selectedBooking.photos} large />
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Pickup location
                  </Typography>
                  <BookingMap
                    latitude={selectedBooking.latitude}
                    longitude={selectedBooking.longitude}
                  />
                  <Link
                    href={`https://www.openstreetmap.org/?mlat=${selectedBooking.latitude}&mlon=${selectedBooking.longitude}#map=17/${selectedBooking.latitude}/${selectedBooking.longitude}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open map
                  </Link>
                </Box>
              </Stack>
            </DialogContent>
            <DialogActions sx={{ justifyContent: 'space-between', flexWrap: 'wrap', p: 2 }}>
              <Button onClick={closeDetail}>Close</Button>
              <Stack direction="row" spacing={1}>
                {selectedBooking.status === 'pending' && (
                  <>
                    <Button color="error" onClick={() => setRejectOpen(true)} disabled={isSaving}>
                      Reject
                    </Button>
                    <Button
                      variant="contained"
                      onClick={() => updateBooking(approveAdminBooking, 'Booking approved.')}
                      disabled={isSaving}
                    >
                      Approve
                    </Button>
                  </>
                )}
                {['approved', 'missed'].includes(selectedBooking.status) && (
                  <Button
                    variant="contained"
                    onClick={() => setRescheduleOpen(true)}
                    disabled={isSaving}
                  >
                    Reschedule
                  </Button>
                )}
              </Stack>
            </DialogActions>
          </>
        )}
      </Dialog>

      <Dialog open={rejectOpen} onClose={() => setRejectOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Reject booking</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="Reason"
            value={rejectReason}
            onChange={(event) => setRejectReason(event.target.value)}
            inputProps={{ maxLength: 1000 }}
            multiline
            minRows={3}
            required
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectOpen(false)}>Cancel</Button>
          <Button
            color="error"
            onClick={submitRejection}
            disabled={isSaving || !rejectReason.trim()}
          >
            Confirm rejection
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={rescheduleOpen}
        onClose={() => setRescheduleOpen(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Reschedule pickup</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            label="New pickup date"
            type="date"
            value={newPickupDate}
            onChange={(event) => setNewPickupDate(event.target.value)}
            InputLabelProps={{ shrink: true }}
            required
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRescheduleOpen(false)}>Cancel</Button>
          <Button onClick={submitReschedule} disabled={isSaving || !newPickupDate}>
            Save date
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
