import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
    Divider,
    FormControl,
    FormControlLabel,
    InputLabel,
    Link,
    MenuItem,
    Select,
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { divIcon } from 'leaflet';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import polyline from '@mapbox/polyline';
import { useAuth } from '../auth/AuthContext';
import {
    generateAdminRoutes,
    getAdminRoutes,
    getRouteDailyTotals,
    getRoutePlanningOptions,
} from '../api/adminRoutes';
import { getAdminBookings } from '../api/adminBookings';
import { routeColors, statusColors } from '../theme';
import 'leaflet/dist/leaflet.css';

const ROUTE_COLORS = routeColors;
const DEFAULT_DEPOT = [-36.815, 174.61];

function toLocalDate(date) {
    const offset = date.getTimezoneOffset();
    return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

function formatMetric(metres) {
    return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${metres} m`;
}

function formatDuration(seconds) {
    const minutes = Math.round(seconds / 60);
    const hours = Math.floor(minutes / 60);
    return hours ? `${hours} h ${minutes % 60} min` : `${minutes} min`;
}

function statusColor(status) {
    return statusColors[status] ?? statusColors.pending;
}

// Completed/Missed stops use their status colour; otherwise keep the route colour.
function stopMarkerColor(stop, routeColor) {
    if (stop.status === 'completed' || stop.status === 'missed') return statusColor(stop.status);
    return routeColor;
}

function FitRoutes({ routes }) {
    const map = useMap();
    // Refit only when the plan itself changes, not when a stop status refreshes.
    const fitKey = routes.map((route) => `${route.id}:${route.geometry ?? ''}:${route.stops.length}`).join('|');
    useEffect(() => {
        const points = routes.flatMap((route) => {
            const geometryPoints = route.geometry ? polyline.decode(route.geometry) : [];
            return geometryPoints.length
                ? geometryPoints
                : route.stops.map((stop) => [stop.latitude, stop.longitude]);
        });
        if (points.length) map.fitBounds(points, { padding: [24, 24], maxZoom: 14 });
        else map.setView(DEFAULT_DEPOT, 10);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map, fitKey]);
    return null;
}

function MarkerDetailPanel({ booking, open, onClose }) {
    if (!open || !booking) return null;
    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>
                <Typography variant="h6">{booking.reference}</Typography>
            </DialogTitle>
            <DialogContent sx={{ minWidth: 420 }}>
                <Stack spacing={1}>
                    <Typography variant="body2"><strong>Address:</strong> {booking.address_text}</Typography>
                    <Typography variant="body2"><strong>Status:</strong> <Chip label={booking.status.charAt(0).toUpperCase() + booking.status.slice(1)} color={booking.status === 'completed' ? 'success' : booking.status === 'missed' ? 'error' : 'default'} size="small" /></Typography>
                    <Typography variant="body2"><strong>Pickup date:</strong> {new Intl.DateTimeFormat('en-NZ', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${booking.pickup_date}T12:00:00`))}</Typography>
                    <Typography variant="body2"><strong>Categories:</strong> {booking.category_names?.join(', ') ?? '—'}</Typography>
                    <Typography variant="body2"><strong>Estimated weight:</strong> {booking.estimated_weight_kg} kg</Typography>
                    <Typography variant="body2"><strong>Estimated volume:</strong> {booking.estimated_volume_l} L</Typography>
                    {(booking.driver_remark || booking.rejection_reason) && (
                        <Typography variant="body2"><strong>Remark:</strong> {booking.driver_remark || booking.rejection_reason}</Typography>
                    )}
                    {booking.photos?.length && (
                        <>
                            <Typography variant="subtitle2" sx={{ mt: 1 }}>Photos ({booking.photos.length}):</Typography>
                            <Stack direction="row" spacing={1}>
                                {booking.photos.slice(0, 6).map((photo) => (
                                    <img key={photo.id} src={`/api/admin/bookings/${booking.id}/photos/${photo.id}`} alt={`Photo ${photo.id}`} sx={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 1 }} />
                                ))}
                            </Stack>
                        </>
                    )}
                </Stack>
            </DialogContent>
            <DialogActions>
                <Button variant="contained" onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
}

export default function AdminRoutesPage() {
    const { user, logout } = useAuth();
    const [pickupDate, setPickupDate] = useState(() => toLocalDate(new Date()));
    const [options, setOptions] = useState(null);
    const [routes, setRoutes] = useState([]);
    const [unassigned, setUnassigned] = useState([]);
    const [assignments, setAssignments] = useState({});
    const [selectedRouteId, setSelectedRouteId] = useState(null);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isGenerating, setIsGenerating] = useState(false);
    const [replaceDialogOpen, setReplaceDialogOpen] = useState(false);
    const [mapMarkers, setMapMarkers] = useState([]);
    const [markerOpen, setMarkerOpen] = useState(false);
    const [selectedMarker, setSelectedMarker] = useState(null);
    const [dailyTotals, setDailyTotals] = useState(null);
    const [pollTimer, setPollTimer] = useState(null);
    const [lastRefresh, setLastRefresh] = useState(null);

    async function loadDate(dateValue) {
        setIsLoading(true);
        setError('');
        try {
            const [planning, savedRoutes] = await Promise.all([
                getRoutePlanningOptions(dateValue),
                getAdminRoutes(dateValue),
            ]);
            setOptions(planning);
            setRoutes(savedRoutes);
            setUnassigned([]);
            setSelectedRouteId(savedRoutes[0]?.id ?? null);
            setAssignments((previous) => {
                const next = {};
                planning.drivers.forEach((driver) => {
                    next[driver.id] = previous[driver.id] ?? '';
                });
                return next;
            });
        } catch (requestError) {
            setError(requestError.message);
            setOptions(null);
            setRoutes([]);
        } finally {
            setIsLoading(false);
        }
    }

    async function loadMapMarkers(dateValue) {
        try {
            const bookings = await getAdminBookings({ status: 'all', pickupDate: dateValue });
            const markers = bookings
                .filter((booking) => booking.status !== 'rejected')
                .map((booking) => ({
                    id: `booking-${booking.id}`,
                    booking_id: booking.id,
                    reference: booking.reference,
                    address_text: booking.address_text,
                    status: booking.status,
                    category_names: booking.category_names,
                    estimated_weight_kg: booking.estimated_weight_kg,
                    estimated_volume_l: booking.estimated_volume_l,
                    driver_remark: booking.driver_remark,
                    photos: booking.photos,
                    pickup_date: booking.pickup_date,
                    latitude: booking.latitude,
                    longitude: booking.longitude,
                }));
            setMapMarkers(markers);
        } catch (requestError) {
            setError(requestError.message);
        }
    }

    async function refreshRoutes(dateValue) {
        try {
            setRoutes(await getAdminRoutes(dateValue));
        } catch {
            // keep the last known routes if a background refresh fails
        }
    }

    async function loadDailyTotals(dateValue) {
        try {
            const totals = await getRouteDailyTotals(dateValue);
            setDailyTotals(totals);
        } catch (requestError) {
            setDailyTotals(null);
        }
    }

    function startPolling() {
        if (pollTimer) clearInterval(pollTimer);
        const timer = setInterval(() => {
            refreshRoutes(pickupDate);
            loadMapMarkers(pickupDate);
            loadDailyTotals(pickupDate);
            setLastRefresh(new Date().toISOString());
        }, 60_000);
        setPollTimer(timer);
    }

    function stopPolling() {
        if (pollTimer) clearInterval(pollTimer);
        setPollTimer(null);
    }

    useEffect(() => {
        loadDate(pickupDate);
        loadMapMarkers(pickupDate);
        loadDailyTotals(pickupDate);
        startPolling();
        return () => stopPolling();
    }, [pickupDate]);

    useEffect(() => {
        if (routes.length > 0) {
            loadDailyTotals(pickupDate);
        }
    }, [routes, pickupDate]);

    const assignmentPairs = Object.entries(assignments)
        .filter(([, vehicleId]) => vehicleId)
        .map(([driverId, vehicleId]) => ({
            driver_id: Number(driverId),
            vehicle_id: Number(vehicleId),
        }));
    const assignedVehicleIds = assignmentPairs.map((pair) => pair.vehicle_id);
    const duplicateVehicle = new Set(assignedVehicleIds).size !== assignedVehicleIds.length;
    const fairShare = assignmentPairs.length
        ? Math.ceil((options?.candidate_booking_count ?? 0) / assignmentPairs.length)
        : 0;
    const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? routes[0] ?? null;
    const mapRoutes = useMemo(() => routes, [routes]);

    function changeVehicle(driverId, vehicleId) {
        setAssignments((current) => ({ ...current, [driverId]: vehicleId }));
    }

    async function doGenerate() {
        if (!options || options.candidate_booking_count === 0) {
            setError('No Approved bookings for this date.');
            return;
        }
        if (!assignmentPairs.length) {
            setError('Choose at least one driver and vehicle.');
            return;
        }
        if (duplicateVehicle) {
            setError('Each vehicle can only be assigned to one driver.');
            return;
        }
        setIsGenerating(true);
        setError('');
        setNotice('');
        try {
            const result = await generateAdminRoutes({ pickup_date: pickupDate, assignments: assignmentPairs });
            setRoutes(result.routes);
            setUnassigned(result.unassigned);
            setSelectedRouteId(result.routes[0]?.id ?? null);
            setNotice(`Generated ${result.routes.length} route${result.routes.length === 1 ? '' : 's'}.`);
            setReplaceDialogOpen(false);
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setIsGenerating(false);
        }
    }

    function requestGenerate() {
        if ((options?.candidate_booking_count ?? 0) === 0) {
            setError('No Approved bookings for this date.');
            return;
        }
        if (routes.length > 0) {
            if (!options.replacement_allowed) {
                setError(options.replacement_block_reason || 'Routes for this date are already in progress');
                return;
            }
            setReplaceDialogOpen(true);
            return;
        }
        doGenerate();
    }

    function handleMarkerClick(marker) {
        setSelectedMarker(marker);
        setMarkerOpen(true);
    }

    return (
        <Container maxWidth="xl" sx={{ py: { xs: 2, sm: 3 } }}>
            <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1.5}
                justifyContent="space-between"
                alignItems={{ xs: 'stretch', sm: 'center' }}
                sx={{ mb: 2 }}
            >
                <Box>
                    <Typography variant="overline" color="primary.main">KohaRoute · Admin</Typography>
                    <Typography component="h1" variant="h4">Route planning</Typography>
                </Box>
                <Stack direction="row" spacing={1.5} alignItems="center">
                    <Link component={RouterLink} to="/admin" underline="hover">Booking review</Link>
                    <Link component={RouterLink} to="/admin/vehicles" underline="hover">Vehicles</Link>
                    <Typography color="text.secondary">{user?.full_name}</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>{lastRefresh ? `Live · refreshed ${new Intl.DateTimeFormat('en-NZ', { hour: '2-digit', minute: '2-digit' }).format(new Date(lastRefresh))}` : ''}</Typography>
                    <Button variant="outlined" onClick={logout}>Log out</Button>
                </Stack>
            </Stack>

            {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}
            {notice && <Alert severity="success" onClose={() => setNotice('')} sx={{ mb: 2 }}>{notice}</Alert>}

            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
                <TextField
                    label="Pickup date"
                    type="date"
                    value={pickupDate}
                    onChange={(event) => setPickupDate(event.target.value)}
                    InputLabelProps={{ shrink: true }}
                    sx={{ width: { xs: '100%', md: 220 } }}
                />
                <Alert severity="info" sx={{ flex: 1, alignItems: 'center' }}>
                    {options?.approved_booking_count ?? 0} Approved bookings
                    {options?.existing_route_count ? ` · ${options.candidate_booking_count} total plan candidates including saved stops` : ''}
                    {' · '}fair-share target: {fairShare || '—'} stops per assigned driver
                </Alert>
            </Stack>

            {dailyTotals && (
                <Box sx={{ mb: 2, bgcolor: 'background.paper', p: 2, borderRadius: 3, border: 1, borderColor: 'divider' }}>
                    <Typography variant="subtitle2" color="text.secondary">Daily estimates &bull; {new Intl.DateTimeFormat('en-NZ', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${dailyTotals.pickup_date}T12:00:00`))}</Typography>
                    <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#E3EDEA', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Planned weight</Typography>
                            <Typography variant="h6">{dailyTotals.planned_weight_kg} kg</Typography>
                        </Box>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#E3EDEA', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Planned volume</Typography>
                            <Typography variant="h6">{dailyTotals.planned_volume_l} L</Typography>
                        </Box>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#DDF1E4', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Completed weight</Typography>
                            <Typography variant="h6">{dailyTotals.completed_weight_kg} kg</Typography>
                        </Box>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#DDF1E4', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Completed volume</Typography>
                            <Typography variant="h6">{dailyTotals.completed_volume_l} L</Typography>
                        </Box>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#F8DEDA', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Missed stops</Typography>
                            <Typography variant="h6">{dailyTotals.missed_count}</Typography>
                        </Box>
                        <Box sx={{ flex: 1, textAlign: 'center', p: 1, bgcolor: '#E8ECEB', borderRadius: 1 }}>
                            <Typography variant="caption" color="text.secondary">Routes</Typography>
                            <Typography variant="h6">{dailyTotals.route_count}</Typography>
                        </Box>
                    </Stack>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>All figures are booking estimates (drivers never enter a real weight).</Typography>
                </Box>
            )}

            <Stack direction={{ xs: 'column', xl: 'row' }} spacing={2} alignItems="stretch">
                <Box sx={{ width: { xs: '100%', xl: 360 }, flexShrink: 0 }}>
                    <Typography variant="h6" sx={{ mb: 1 }}>Driver and vehicle pairing</Typography>
                    {isLoading ? (
                        <Typography color="text.secondary">Loading planning options…</Typography>
                    ) : !options?.drivers.length ? (
                        <Alert severity="warning">No active drivers are available.</Alert>
                    ) : options.vehicles.length === 0 ? (
                        <Alert severity="warning">Add an active vehicle before generating routes.</Alert>
                    ) : (
                        <Stack spacing={1.5}>
                            {options.drivers.map((driver) => (
                                <FormControl key={driver.id} fullWidth size="small">
                                    <InputLabel id={`driver-vehicle-${driver.id}`}>{driver.full_name}</InputLabel>
                                    <Select
                                        labelId={`driver-vehicle-${driver.id}`}
                                        label={driver.full_name}
                                        value={assignments[driver.id] ?? ''}
                                        onChange={(event) => changeVehicle(driver.id, event.target.value)}
                                    >
                                        <MenuItem value=""><em>Not assigned</em></MenuItem>
                                        {options.vehicles.map((vehicle) => (
                                            <MenuItem key={vehicle.id} value={vehicle.id}>
                                                {vehicle.name} · {vehicle.plate_number} · {vehicle.capacity_kg} kg / {vehicle.capacity_litres} L
                                            </MenuItem>
                                        ))}
                                    </Select>
                                </FormControl>
                            ))}
                            {duplicateVehicle && <Alert severity="error">A vehicle may only be paired with one driver.</Alert>}
                            <Button
                                variant="contained"
                                onClick={requestGenerate}
                                disabled={isLoading || isGenerating || options.candidate_booking_count === 0 || assignmentPairs.length === 0}
                            >
                                {isGenerating ? 'Optimizing routes…' : routes.length ? 'Regenerate routes' : 'Generate routes'}
                            </Button>
                        </Stack>
                    )}

                    {routes.length > 0 && (
                        <Box sx={{ mt: 3 }}>
                            <Typography variant="h6" sx={{ mb: 1 }}>Routes</Typography>
                            <Stack spacing={1}>
                                {routes.map((route) => (
                                    <Button
                                        key={route.id}
                                        onClick={() => setSelectedRouteId(route.id)}
                                        variant={selectedRouteId === route.id ? 'contained' : 'outlined'}
                                        color="inherit"
                                        sx={{ justifyContent: 'flex-start', borderLeft: `6px solid ${route.color}`, textAlign: 'left' }}
                                    >
                                        {route.driver_name} · {route.vehicle_plate_number} · {route.stops.length} stops
                                    </Button>
                                ))}
                            </Stack>
                        </Box>
                    )}

                    {selectedRoute && (
                        <Box sx={{ mt: 2 }}>
                            <Typography variant="subtitle1">{selectedRoute.driver_name} · {selectedRoute.vehicle_name}</Typography>
                            <Typography variant="body2" color="text.secondary">
                                {formatMetric(selectedRoute.total_distance_m)} · {formatDuration(selectedRoute.total_duration_s)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Planned estimates: {selectedRoute.planned_weight_kg} kg · {selectedRoute.planned_volume_l} L
                            </Typography>
                            <Typography variant="body2" color="text.success">
                                Completed estimates: {selectedRoute.completed_weight_kg} kg · {selectedRoute.completed_volume_l} L
                            </Typography>
                            <Stack spacing={0.75} sx={{ mt: 1 }}>
                                {selectedRoute.stops.map((stop) => (
                                    <Box key={stop.booking_id} sx={{ borderLeft: `3px solid ${selectedRoute.color}`, pl: 1 }}>
                                        <Typography variant="body2"><strong>{stop.sequence}.</strong> {stop.address_text}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {stop.reference} · {stop.estimated_weight_kg} kg / {stop.estimated_volume_l} L · {stop.status.charAt(0).toUpperCase() + stop.status.slice(1)}
                                        </Typography>
                                    </Box>
                                ))}
                            </Stack>
                        </Box>
                    )}
                </Box>

                <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ height: { xs: 360, md: 560 }, width: '100%', overflow: 'hidden', borderRadius: 3, border: 1, borderColor: 'divider' }}>
                        <MapContainer center={DEFAULT_DEPOT} zoom={10} style={{ height: '100%', width: '100%' }}>
                            <TileLayer
                                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                            />
                            <FitRoutes routes={mapRoutes} />
                            {mapRoutes.map((route) => {
                                const points = route.geometry ? polyline.decode(route.geometry) : [];
                                return (
                                    <Fragment key={route.id}>
                                        {points.length > 0 && <Polyline positions={points} pathOptions={{ color: route.color, weight: 5 }} />}
                                        {route.stops.map((stop) => (
                                            <Marker
                                                key={`route-${stop.booking_id}`}
                                                position={[stop.latitude, stop.longitude]}
                                                icon={divIcon({
                                                    className: 'koha-route-stop-marker',
                                                    html: `<span style="background:${stopMarkerColor(stop, route.color)};width:26px;height:26px;border-radius:50%;border:2px solid white;color:white;display:flex;align-items:center;justify-content:center;font-weight:700;box-shadow:0 1px 4px #333">${stop.sequence}</span>`,
                                                    iconSize: [26, 26],
                                                    iconAnchor: [13, 13],
                                                })}
                                                onClick={() => handleMarkerClick({
                                                    id: `route-stop-${stop.booking_id}`,
                                                    reference: stop.reference,
                                                    address_text: stop.address_text,
                                                    status: stop.status,
                                                    category_names: stop.category_names,
                                                    estimated_weight_kg: stop.estimated_weight_kg,
                                                    estimated_volume_l: stop.estimated_volume_l,
                                                    driver_remark: stop.remark,
                                                    photos: [],
                                                    pickup_date: pickupDate,
                                                    latitude: stop.latitude,
                                                    longitude: stop.longitude,
                                                })}
                                            >
                                                <Popup>
                                                    <strong>{stop.sequence}. {stop.address_text}</strong><br />
                                                    {stop.reference}<br />
                                                    {stop.estimated_weight_kg} kg · {stop.estimated_volume_l} L
                                                </Popup>
                                            </Marker>
                                        ))}
                                    </Fragment>
                                );
                            })}
                            {mapMarkers.map((marker) => (
                                <Marker
                                    key={marker.id}
                                    position={[marker.latitude, marker.longitude]}
                                    icon={divIcon({
                                        className: 'koha-booking-marker',
                                        html: `<span style="background:${statusColor(marker.status)};width:22px;height:22px;border-radius:50%;border:2px solid white;color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:10px;box-shadow:0 1px 4px #333">${marker.status.charAt(0).toUpperCase()}</span>`,
                                        iconSize: [22, 22],
                                        iconAnchor: [11, 11],
                                    })}
                                    onClick={() => handleMarkerClick(marker)}
                                >
                                    <Popup>
                                        <strong>{marker.reference}</strong><br />
                                        {marker.address_text}<br />
                                        {marker.status.charAt(0).toUpperCase() + marker.status.slice(1)} · {marker.estimated_weight_kg} kg / {marker.estimated_volume_l} L
                                    </Popup>
                                </Marker>
                            ))}
                        </MapContainer>
                    </Box>
                    {unassigned.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                            <Alert severity="warning" sx={{ mb: 1 }}>
                                {unassigned.length} booking{unassigned.length === 1 ? '' : 's'} unassigned; they remain Approved for the next plan.
                            </Alert>
                            <Stack spacing={0.5}>
                                {unassigned.map((booking) => (
                                    <Typography key={booking.id} variant="body2">
                                        {booking.reference} · {booking.address_text} · {booking.estimated_weight_kg} kg / {booking.estimated_volume_l} L
                                    </Typography>
                                ))}
                            </Stack>
                        </Box>
                    )}
                </Box>
            </Stack>

            <Dialog open={replaceDialogOpen} onClose={() => setReplaceDialogOpen(false)}>
                <DialogTitle>Replace existing routes?</DialogTitle>
                <DialogContent>
                    <Typography>The existing plan for this date will be replaced after ORS returns a valid new plan.</Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setReplaceDialogOpen(false)}>Cancel</Button>
                    <Button variant="contained" onClick={doGenerate} disabled={isGenerating}>
                        Replace routes
                    </Button>
                </DialogActions>
            </Dialog>

            <MarkerDetailPanel
                booking={selectedMarker}
                open={markerOpen}
                onClose={() => { setMarkerOpen(false); setSelectedMarker(null); }}
            />
        </Container>
    );
}