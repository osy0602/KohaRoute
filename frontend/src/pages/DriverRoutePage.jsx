import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Collapse,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Link,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { divIcon } from 'leaflet';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import polyline from '@mapbox/polyline';
import { useAuth } from '../auth/AuthContext';
import { fetchDriverPhoto, getMyRoutes, getNzToday, updateMyStop } from '../api/driverRoutes';
import { formatVolumeM3 } from '../utils/volume';
import { ApiError } from '../api/http';
import { statusColors } from '../theme';
import 'leaflet/dist/leaflet.css';

const DEFAULT_DEPOT = [-36.815, 174.61];
const TAP_TARGET = 48; // px; comfortably above the 44px minimum for touch
const WRAP_LONG_TEXT = { overflowWrap: 'anywhere', minWidth: 0 };

/** Decode the saved route line; a corrupt value must never blank the whole page. */
function decodePath(geometry) {
  if (!geometry) return [];
  try {
    return polyline.decode(geometry);
  } catch {
    return [];
  }
}

/** Show a friendly message for server failures, but keep the network message as is. */
function loadErrorMessage(error) {
  if (error instanceof ApiError && error.status > 0) return 'Could not load your route.';
  return error?.message || 'Could not load your route.';
}

function formatDate(value) {
  return new Intl.DateTimeFormat('en-NZ', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`));
}

function formatDistance(metres) {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${metres} m`;
}

function formatDuration(seconds) {
  const minutes = Math.round(seconds / 60);
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours} h ${minutes % 60} min` : `${minutes} min`;
}

function stopIcon(stop, isNext) {
  const background = isNext
    ? '#12343B'
    : stop.status === 'completed'
      ? statusColors.completed
      : stop.status === 'missed'
        ? statusColors.missed
        : statusColors.scheduled;
  const size = isNext ? 36 : 28;
  return divIcon({
    className: 'koha-driver-stop-marker',
    html: `<span style="background:${background};width:${size}px;height:${size}px;border-radius:50%;border:2px solid white;color:white;display:flex;align-items:center;justify-content:center;font-weight:700;box-shadow:0 1px 4px #333">${Number(stop.sequence)}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function DriverMap({ route, nextBookingId }) {
  const map = useMap();
  // Decode once per saved line. Keyed on the geometry (not the route object) so marking a
  // stop done does not reset the zoom and position the driver has chosen.
  const path = useMemo(() => decodePath(route.geometry), [route.geometry]);
  useEffect(() => {
    if (path.length) map.fitBounds(path, { padding: [24, 24], maxZoom: 14 });
    else map.setView(DEFAULT_DEPOT, 10);
  }, [map, path]);

  return (
    <>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {path.length > 0 && <Polyline positions={path} pathOptions={{ color: '#247BA0', weight: 5 }} />}
      {route.stops.map((stop) => (
        <Marker
          key={stop.booking_id}
          position={[stop.latitude, stop.longitude]}
          icon={stopIcon(stop, stop.booking_id === nextBookingId)}
        >
          <Popup>
            <strong>{stop.sequence}. {stop.address_text}</strong>
            <br />
            {stop.reference}
          </Popup>
        </Marker>
      ))}
    </>
  );
}

const PHOTO_BOX = {
  width: 92,
  height: 92,
  borderRadius: 1,
  border: '1px solid',
  borderColor: 'divider',
};

function DriverPhoto({ routeId, stop, photo, index }) {
  const [imageUrl, setImageUrl] = useState('');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl = '';
    setImageUrl('');
    setFailed(false);
    fetchDriverPhoto(routeId, stop.booking_id, photo.id, controller.signal)
      .then((url) => {
        objectUrl = url;
        setImageUrl(url);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [routeId, stop.booking_id, photo.id]);

  if (failed) {
    // Tell the driver a photo exists but could not be shown, rather than hiding it.
    return (
      <Box
        role="img"
        aria-label={`Donation item ${index + 1} could not be loaded`}
        sx={{
          ...PHOTO_BOX,
          display: 'grid',
          placeItems: 'center',
          p: 0.5,
          textAlign: 'center',
          color: 'text.secondary',
          typography: 'caption',
        }}
      >
        Photo unavailable
      </Box>
    );
  }
  if (!imageUrl) {
    return <Box aria-hidden sx={{ ...PHOTO_BOX, bgcolor: 'action.hover' }} />;
  }
  return (
    <Box
      component="img"
      src={imageUrl}
      alt={`Donation item ${index + 1}`}
      sx={{ ...PHOTO_BOX, objectFit: 'cover' }}
    />
  );
}

function StopCard({ route, stop, isNext, onUpdate, isUpdating }) {
  const [expanded, setExpanded] = useState(isNext);
  const [missedDialogOpen, setMissedDialogOpen] = useState(false);
  const [remark, setRemark] = useState('');
  const scheduled = stop.status === 'scheduled';
  const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(`${stop.latitude},${stop.longitude}`)}`;

  useEffect(() => {
    if (isNext) setExpanded(true);
  }, [isNext]);

  async function submitMissed() {
    if (!remark.trim()) return;
    const success = await onUpdate(route.id, stop.booking_id, 'missed', remark.trim());
    if (success) {
      setMissedDialogOpen(false);
      setRemark('');
    }
  }

  return (
    <Card
      variant="outlined"
      sx={{
        borderRadius: 1,
        borderColor: isNext ? route.color : 'divider',
        borderWidth: isNext ? 2 : 1,
      }}
    >
      <CardContent sx={{ p: { xs: 2, sm: 2.5 }, '&:last-child': { pb: { xs: 2, sm: 2.5 } } }}>
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={1.5} alignItems="flex-start" justifyContent="space-between">
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="overline" color={isNext ? 'primary.main' : 'text.secondary'}>
                {isNext ? 'Next stop' : `Stop ${stop.sequence}`}
              </Typography>
              <Typography component="h2" variant="h6" sx={WRAP_LONG_TEXT}>
                {stop.address_text}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={WRAP_LONG_TEXT}>
                {stop.reference} · {stop.status.charAt(0).toUpperCase() + stop.status.slice(1)}
              </Typography>
            </Box>
            <Button
              aria-label={`${expanded ? 'Hide' : 'Show'} details for stop ${stop.sequence}`}
              onClick={() => setExpanded((value) => !value)}
              sx={{ minWidth: 44, minHeight: 44, flexShrink: 0 }}
            >
              {expanded ? 'Hide' : 'Details'}
            </Button>
          </Stack>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <Button
              component="a"
              href={mapsUrl}
              target="_blank"
              rel="noopener noreferrer"
              variant="outlined"
              sx={{ minHeight: TAP_TARGET, flex: { sm: 1 } }}
            >
              Navigate with Google Maps
            </Button>
            {scheduled && (
              <>
                <Button
                  variant="contained"
                  onClick={() => onUpdate(route.id, stop.booking_id, 'completed', '')}
                  disabled={isUpdating}
                  sx={{ minHeight: TAP_TARGET, flex: { sm: 1 } }}
                >
                  {isUpdating ? <CircularProgress size={22} color="inherit" /> : 'Mark completed'}
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  onClick={() => setMissedDialogOpen(true)}
                  disabled={isUpdating}
                  sx={{ minHeight: TAP_TARGET, flex: { sm: 1 } }}
                >
                  Mark missed
                </Button>
              </>
            )}
          </Stack>

          <Collapse in={expanded}>
            <Stack spacing={1.5} sx={{ pt: 1 }}>
              <Box>
                <Typography variant="subtitle2">Donor</Typography>
                <Typography sx={WRAP_LONG_TEXT}>{stop.donor_name}</Typography>
                <Link
                  href={`tel:${stop.contact_number.replace(/[^+\d]/g, '')}`}
                  underline="hover"
                  sx={{ display: 'inline-flex', alignItems: 'center', minHeight: 44, ...WRAP_LONG_TEXT }}
                >
                  {stop.contact_number}
                </Link>
              </Box>
              <Box>
                <Typography variant="subtitle2">Categories</Typography>
                <Typography sx={WRAP_LONG_TEXT}>{stop.category_names.join(', ')}</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary">
                Estimated load: {stop.estimated_weight_kg} kg · {formatVolumeM3(stop.estimated_volume_l)}
              </Typography>
              <Box>
                <Typography variant="subtitle2">Description</Typography>
                <Typography sx={{ whiteSpace: 'pre-wrap', ...WRAP_LONG_TEXT }}>
                  {stop.description || 'No description provided.'}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 0.75 }}>Photos</Typography>
                {stop.photos.length ? (
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    {expanded &&
                      stop.photos.map((photo, index) => (
                        <DriverPhoto key={photo.id} routeId={route.id} stop={stop} photo={photo} index={index} />
                      ))}
                  </Stack>
                ) : <Typography color="text.secondary">No photos attached.</Typography>}
              </Box>
              {stop.remark && (
                <Alert severity={stop.status === 'missed' ? 'warning' : 'success'} sx={WRAP_LONG_TEXT}>
                  {stop.remark}
                </Alert>
              )}
            </Stack>
          </Collapse>
        </Stack>
      </CardContent>

      <Dialog open={missedDialogOpen} onClose={() => setMissedDialogOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>Mark pickup missed</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            required
            multiline
            minRows={3}
            label="Reason for missing this pickup"
            value={remark}
            onChange={(event) => setRemark(event.target.value)}
            helperText="A remark is required."
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMissedDialogOpen(false)} sx={{ minHeight: 44 }}>Cancel</Button>
          <Button
            color="warning"
            onClick={submitMissed}
            disabled={!remark.trim() || isUpdating}
            sx={{ minHeight: 44 }}
          >
            Confirm missed
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
}

export default function DriverRoutePage() {
  const { user, logout } = useAuth();
  const [pickupDate, setPickupDate] = useState('');
  const [nzToday, setNzToday] = useState('');
  const [routes, setRoutes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [retry, setRetry] = useState(0);
  const [todayRetry, setTodayRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setError('');
    getNzToday()
      .then((result) => {
        if (active) {
          setNzToday(result);
          setPickupDate(result);
        }
      })
      .catch((requestError) => {
        if (active) {
          setError(loadErrorMessage(requestError));
          setIsLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [todayRetry]);

  useEffect(() => {
    if (!pickupDate) return undefined;
    let active = true;
    setIsLoading(true);
    setError('');
    setActionError('');
    setNotice('');
    setRoutes([]);
    getMyRoutes(pickupDate)
      .then((result) => {
        if (active) setRoutes(result);
      })
      .catch((requestError) => {
        if (active) setError(loadErrorMessage(requestError));
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [pickupDate, retry]);

  const route = routes[0] ?? null;
  const orderedStops = route ? [...route.stops].sort((left, right) => left.sequence - right.sequence) : [];
  const nextStop = orderedStops.find((stop) => stop.status === 'scheduled') ?? null;
  const remainingStops = orderedStops.filter((stop) => stop.booking_id !== nextStop?.booking_id);

  async function handleStopUpdate(routeId, bookingId, status, remark) {
    setIsUpdating(true);
    setActionError('');
    setNotice('');
    try {
      const updatedStop = await updateMyStop(routeId, bookingId, status, remark);
      setRoutes((currentRoutes) => currentRoutes.map((currentRoute) => {
        if (currentRoute.id !== routeId) return currentRoute;
        const stops = currentRoute.stops.map((stop) =>
          stop.booking_id === bookingId ? { ...stop, ...updatedStop } : stop,
        );
        const activeStatuses = stops.map((stop) => stop.status);
        const nextRouteStatus = activeStatuses.every((item) => ['completed', 'missed'].includes(item))
          ? 'done'
          : activeStatuses.some((item) => ['completed', 'missed'].includes(item))
            ? 'in_progress'
            : 'planned';
        return { ...currentRoute, stops, status: nextRouteStatus };
      }));
      setNotice(status === 'completed' ? 'Pickup marked completed.' : 'Pickup marked missed.');
      return true;
    } catch (requestError) {
      setActionError(requestError.message || 'Could not update this pickup. Try again.');
      return false;
    } finally {
      setIsUpdating(false);
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: { xs: 2, sm: 4 }, px: { xs: 2, sm: 3 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        sx={{ mb: 2.5 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main">KohaRoute · Driver</Typography>
          <Typography component="h1" variant="h4">My route</Typography>
          <Typography color="text.secondary">{user?.full_name}</Typography>
        </Box>
        <Button variant="outlined" onClick={logout} sx={{ minHeight: 44, alignSelf: { xs: 'flex-start', sm: 'center' } }}>
          Log out
        </Button>
      </Stack>

      <TextField
        label="Route date"
        type="date"
        value={pickupDate}
        onChange={(event) => {
          if (event.target.value) setPickupDate(event.target.value);
        }}
        InputLabelProps={{ shrink: true }}
        sx={{ width: { xs: '100%', sm: 240 }, mb: 2 }}
      />

      {notice && <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>{notice}</Alert>}
      {actionError && (
        <Alert severity="error" onClose={() => setActionError('')} sx={{ mb: 2, ...WRAP_LONG_TEXT }}>
          {actionError}
        </Alert>
      )}
      {error && (
        <Alert
          severity="error"
          action={(
            <Button
              color="inherit"
              onClick={() => pickupDate
                ? setRetry((value) => value + 1)
                : setTodayRetry((value) => value + 1)}
              sx={{ minHeight: 44, minWidth: 44 }}
            >
              Try again
            </Button>
          )}
          sx={{ mb: 2, alignItems: 'center', ...WRAP_LONG_TEXT }}
        >
          {error}
        </Alert>
      )}
      {isLoading && (
        <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 180 }}>
          <CircularProgress aria-label="Loading route" />
        </Box>
      )}
      {!isLoading && !error && !route && (
        <Alert severity="info">{pickupDate === nzToday ? 'No route assigned for today' : 'No route assigned for this day'}</Alert>
      )}
      {!isLoading && route && (
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6">{formatDate(route.pickup_date)}</Typography>
            <Typography color="text.secondary" sx={WRAP_LONG_TEXT}>
              {route.vehicle_name} · {route.vehicle_plate_number} · {formatDistance(route.total_distance_m)} · {formatDuration(route.total_duration_s)}
            </Typography>
          </Box>
          <Box sx={{ height: { xs: 260, sm: 340 }, overflow: 'hidden', borderRadius: 1 }}>
            <MapContainer
              center={DEFAULT_DEPOT}
              zoom={10}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={false}
            >
              <DriverMap route={route} nextBookingId={nextStop?.booking_id} />
            </MapContainer>
          </Box>
          {orderedStops.length === 0 && (
            <Alert severity="warning">
              No stops on this route. Please contact the office if you expected pickups.
            </Alert>
          )}
          {nextStop && (
            <StopCard
              route={route}
              stop={nextStop}
              isNext
              onUpdate={handleStopUpdate}
              isUpdating={isUpdating}
            />
          )}
          {remainingStops.map((stop) => (
            <StopCard
              key={stop.booking_id}
              route={route}
              stop={stop}
              isNext={false}
              onUpdate={handleStopUpdate}
              isUpdating={isUpdating}
            />
          ))}
        </Stack>
      )}
    </Container>
  );
}
