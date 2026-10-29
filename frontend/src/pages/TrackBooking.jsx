import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Link as RouterLink, useSearchParams } from 'react-router-dom';
import { apiRequest } from '../api/http';

const STATUS_LABELS = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  scheduled: 'Scheduled',
  completed: 'Completed',
  missed: 'Missed',
};

function formatDate(value) {
  return new Intl.DateTimeFormat('en-NZ', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`));
}

export default function TrackBooking() {
  const [searchParams] = useSearchParams();
  const [reference, setReference] = useState(searchParams.get('reference') ?? '');
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const normalizedReference = reference.trim();
    if (!normalizedReference) {
      setError('Enter your booking reference.');
      setBooking(null);
      return;
    }

    setIsLoading(true);
    setError('');
    setBooking(null);
    try {
      const result = await apiRequest(
        `/api/bookings/track/${encodeURIComponent(normalizedReference)}`,
      );
      setBooking(result);
    } catch (requestError) {
      setError(requestError.status === 404 ? 'No booking found' : requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Container maxWidth="sm" sx={{ py: { xs: 3, sm: 6 } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Typography variant="overline" color="primary.main">
          Te Manawa Community Centre
        </Typography>
        <Link component={RouterLink} to="/book" underline="hover">
          Book a pickup
        </Link>
      </Stack>
      <Typography component="h1" variant="h3" sx={{ mb: 1 }}>
        Track a booking
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Enter the reference shown when you booked your pickup.
      </Typography>

      <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'grid', gap: 2 }}>
        <TextField
          label="Booking reference"
          value={reference}
          onChange={(event) => setReference(event.target.value)}
          inputProps={{ maxLength: 24, autoCapitalize: 'characters' }}
          error={Boolean(error && error !== 'No booking found')}
          helperText={error && error !== 'No booking found' ? error : ' '}
          fullWidth
        />
        <Button type="submit" variant="contained" size="large" disabled={isLoading}>
          {isLoading ? 'Checking…' : 'Check booking'}
        </Button>
      </Box>

      {error === 'No booking found' && (
        <Alert severity="info" sx={{ mt: 3 }}>
          No booking found
        </Alert>
      )}

      {booking && (
        <Paper variant="outlined" sx={{ mt: 3, p: 2.5, borderRadius: 1 }}>
          <Stack spacing={1.5}>
            <Box>
              <Typography variant="overline" color="text.secondary">
                Status
              </Typography>
              <Typography component="p" variant="h5">
                {STATUS_LABELS[booking.status] ?? booking.status}
              </Typography>
            </Box>
            <Box>
              <Typography variant="overline" color="text.secondary">
                Pickup date
              </Typography>
              <Typography>{formatDate(booking.pickup_date)}</Typography>
            </Box>
            <Box>
              <Typography variant="overline" color="text.secondary">
                Pickup area
              </Typography>
              <Typography>{booking.address_area}</Typography>
            </Box>
            {booking.rejection_reason && (
              <Alert severity="warning">Reason: {booking.rejection_reason}</Alert>
            )}
            {booking.missed_message && <Alert severity="info">{booking.missed_message}</Alert>}
          </Stack>
        </Paper>
      )}
    </Container>
  );
}
