import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Container,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  InputLabel,
  Link,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { apiRequest } from '../api/http';
import { formatVolumeM3 } from '../utils/volume';

const PRIVACY_NOTICE =
  'We use your name, contact number, address and photos only to arrange and complete this pickup. Only Te Manawa Community Centre staff and the driver collecting your items can see them, and they are not shared or used for anything else.';

function formatDate(value) {
  return new Intl.DateTimeFormat('en-NZ', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date(`${value}T12:00:00`));
}

function FormFieldError({ errors, field }) {
  return errors[field] ? <FormHelperText error>{errors[field]}</FormHelperText> : null;
}

export default function BookPickup() {
  const [options, setOptions] = useState(null);
  const [optionsError, setOptionsError] = useState('');
  const [form, setForm] = useState({
    donorName: '',
    contactNumber: '',
    addressText: '',
    addressToken: '',
    pickupDate: '',
    size: '',
    quantity: '1',
    categoryIds: [],
    description: '',
    photos: [],
  });
  const [suggestions, setSuggestions] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState(null);
  const [copied, setCopied] = useState(false);

  async function loadOptions() {
    setOptionsError('');
    try {
      setOptions(await apiRequest('/api/bookings/options'));
    } catch (error) {
      setOptionsError(error.message);
    }
  }

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    if (form.addressText.trim().length < 3 || form.addressToken) {
      setSuggestions([]);
      setIsSearching(false);
      return undefined;
    }
    let active = true;
    const timer = window.setTimeout(async () => {
      setIsSearching(true);
      try {
        const result = await apiRequest(
          `/api/bookings/address-suggestions?query=${encodeURIComponent(form.addressText)}`,
        );
        if (active) setSuggestions(result);
      } catch (error) {
        if (active) setSubmitError(error.message);
      } finally {
        if (active) setIsSearching(false);
      }
    }, 400);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [form.addressText, form.addressToken]);

  const selectedPreset = options?.size_presets.find((preset) => preset.key === form.size);
  const quantity = Number(form.quantity);
  const estimatedWeight = selectedPreset && quantity > 0 ? selectedPreset.weight_kg * quantity : 0;
  const estimatedVolume = selectedPreset && quantity > 0 ? selectedPreset.volume_l * quantity : 0;

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: '' }));
    setSubmitError('');
  }

  function selectSuggestion(suggestion) {
    setForm((current) => ({
      ...current,
      addressText: suggestion.label,
      addressToken: suggestion.token,
    }));
    setSuggestions([]);
    setErrors((current) => ({ ...current, address: '' }));
  }

  function updatePhotos(files) {
    const chosen = Array.from(files ?? []);
    if (!options) return;
    if (chosen.length > options.max_photos) {
      update('photos', chosen.slice(0, options.max_photos));
      setErrors((current) => ({
        ...current,
        photos: `Choose no more than ${options.max_photos} photos.`,
      }));
      return;
    }
    const oversized = chosen.find((file) => file.size > options.max_photo_size_bytes);
    if (oversized) {
      update('photos', chosen);
      setErrors((current) => ({ ...current, photos: `${oversized.name} is larger than 5 MB.` }));
      return;
    }
    const unsupported = chosen.find((file) => !['image/jpeg', 'image/png'].includes(file.type));
    update('photos', chosen);
    if (unsupported) {
      setErrors((current) => ({ ...current, photos: `${unsupported.name} is not a JPG or PNG.` }));
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const nextErrors = {};
    if (!form.donorName.trim()) nextErrors.donor_name = 'Enter your name.';
    if (!form.contactNumber.trim()) nextErrors.contact_number = 'Enter your contact number.';
    if (!form.addressToken) nextErrors.address = 'Choose an Auckland address from the suggestions.';
    if (!form.pickupDate) nextErrors.pickup_date = 'Choose an available pickup date.';
    if (!form.size) nextErrors.size = 'Choose an item size.';
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > (options?.max_quantity ?? 10)) {
      nextErrors.quantity = `Enter a whole number from 1 to ${options?.max_quantity ?? 10}.`;
    }
    if (form.categoryIds.length === 0) nextErrors.category_ids = 'Choose at least one category.';
    if (form.photos.length < (options?.min_photos ?? 1)) nextErrors.photos = 'Choose at least one photo.';
    if (form.description.length > (options?.description_max_chars ?? 300)) {
      nextErrors.description = 'Description is too long.';
    }
    setErrors(nextErrors);
    setSubmitError('');
    if (Object.keys(nextErrors).length > 0) return;

    const body = new FormData();
    body.append('donor_name', form.donorName);
    body.append('contact_number', form.contactNumber);
    body.append('address_token', form.addressToken);
    body.append('pickup_date', form.pickupDate);
    body.append('size', form.size);
    body.append('quantity', String(quantity));
    form.categoryIds.forEach((id) => body.append('category_ids', String(id)));
    if (form.description.trim()) body.append('description', form.description.trim());
    form.photos.forEach((photo) => body.append('photos', photo));

    setIsSubmitting(true);
    try {
      setConfirmation(await apiRequest('/api/bookings', { method: 'POST', body }));
    } catch (error) {
      if (error.field) setErrors((current) => ({ ...current, [error.field]: error.message }));
      else setSubmitError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function copyReference() {
    try {
      await navigator.clipboard.writeText(confirmation.reference);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  if (confirmation) {
    return (
      <Container maxWidth="sm" sx={{ py: { xs: 4, sm: 8 } }}>
        <Typography variant="overline" color="success.main">Booking received</Typography>
        <Typography component="h1" variant="h3" sx={{ mb: 2 }}>Your pickup request is in.</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>
          Keep this reference to check your booking status.
        </Typography>
        <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 1, mb: 3 }}>
          <Typography variant="overline">Booking reference</Typography>
          <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
            <Typography variant="h5" component="p" sx={{ fontFamily: 'monospace', overflowWrap: 'anywhere' }}>
              {confirmation.reference}
            </Typography>
            <Button onClick={copyReference} variant="outlined">{copied ? 'Copied' : 'Copy'}</Button>
          </Stack>
        </Paper>
        <Typography>Pickup date: {formatDate(confirmation.pickup_date)}</Typography>
        <Typography>Status: Pending review</Typography>
        <Typography color="text.secondary" sx={{ mt: 2 }}>
          Check the booking status and pickup date using this reference.
        </Typography>
        <Button
          component={RouterLink}
          to={`/track?reference=${encodeURIComponent(confirmation.reference)}`}
          variant="contained"
          sx={{ mt: 2 }}
        >
          Track booking
        </Button>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: { xs: 3, sm: 6 } }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        spacing={2}
        sx={{ mb: 4 }}
      >
        <Box>
          <Typography
            component="p"
            sx={{
              fontFamily: '"Bricolage Grotesque", "Public Sans", system-ui, sans-serif',
              fontWeight: 700,
              // Scales with the screen so the name and both links always share one line.
              fontSize: 'clamp(1.15rem, 3.2vw, 2.1rem)',
              whiteSpace: 'nowrap',
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              color: 'primary.dark',
            }}
          >
            Te Manawa Community Centre
          </Typography>
          <Box sx={{ mt: 1, width: 72, height: 5, borderRadius: 3, bgcolor: 'warning.main' }} />
        </Box>
        <Stack direction="row" spacing={3} sx={{ whiteSpace: 'nowrap', flexShrink: 0 }}>
          <Link component={RouterLink} to="/track" underline="hover">Track a booking</Link>
          <Link component={RouterLink} to="/login" underline="hover">Staff login</Link>
        </Stack>
      </Stack>
      <Typography component="h1" variant="h3" sx={{ mb: 1 }}>Book a pickup</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        Request a weekday collection for reusable items.
      </Typography>

      {optionsError && (
        <Alert severity="error" action={<Button color="inherit" onClick={loadOptions}>Try again</Button>} sx={{ mb: 2 }}>
          {optionsError}
        </Alert>
      )}
      {submitError && <Alert severity="error" sx={{ mb: 2 }}>{submitError}</Alert>}

      <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'grid', gap: 2.5 }}>
        <TextField
          label="Your name"
          value={form.donorName}
          onChange={(event) => update('donorName', event.target.value)}
          error={Boolean(errors.donor_name)}
          helperText={errors.donor_name}
          required
          fullWidth
        />
        <TextField
          label="Contact number"
          type="tel"
          autoComplete="tel"
          value={form.contactNumber}
          onChange={(event) => update('contactNumber', event.target.value)}
          error={Boolean(errors.contact_number)}
          helperText={errors.contact_number}
          required
          fullWidth
        />

        <Box>
          <TextField
            label="Auckland pickup address"
            value={form.addressText}
            onChange={(event) => {
              setForm((current) => ({ ...current, addressText: event.target.value, addressToken: '' }));
              setErrors((current) => ({ ...current, address: '' }));
            }}
            error={Boolean(errors.address)}
            helperText={errors.address || (isSearching ? 'Searching Auckland addresses…' : 'Choose an address from the suggestions.')}
            inputProps={{ autoComplete: 'street-address' }}
            required
            fullWidth
          />
          {suggestions.length > 0 && (
            <Paper variant="outlined" sx={{ mt: 0.5, borderRadius: 1 }}>
              {suggestions.map((suggestion) => (
                <Button
                  key={suggestion.token}
                  onClick={() => selectSuggestion(suggestion)}
                  sx={{ display: 'block', width: '100%', px: 2, py: 1.25, textAlign: 'left', justifyContent: 'flex-start' }}
                >
                  {suggestion.label}
                </Button>
              ))}
            </Paper>
          )}
        </Box>

        <FormControl error={Boolean(errors.pickup_date)} required>
          <InputLabel id="pickup-date-label">Pickup date</InputLabel>
          <Select
            labelId="pickup-date-label"
            label="Pickup date"
            value={form.pickupDate}
            onChange={(event) => update('pickupDate', event.target.value)}
            disabled={!options}
          >
            {(options?.pickup_dates ?? []).map((day) => (
              <MenuItem key={day} value={day}>{formatDate(day)}</MenuItem>
            ))}
          </Select>
          <FormFieldError errors={errors} field="pickup_date" />
        </FormControl>

        <FormControl error={Boolean(errors.category_ids)} required>
          <Typography component="legend" variant="subtitle1">What are you donating?</Typography>
          <FormGroup>
            {options?.categories.map((category) => (
              <FormControlLabel
                key={category.id}
                control={
                  <Checkbox
                    checked={form.categoryIds.includes(category.id)}
                    onChange={(event) => {
                      const next = event.target.checked
                        ? [...form.categoryIds, category.id]
                        : form.categoryIds.filter((id) => id !== category.id);
                      update('categoryIds', next);
                    }}
                  />
                }
                label={category.name}
              />
            ))}
          </FormGroup>
          <FormFieldError errors={errors} field="category_ids" />
        </FormControl>

        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
          <FormControl error={Boolean(errors.size)} required fullWidth>
            <InputLabel id="size-label">Donation size</InputLabel>
            <Select
              labelId="size-label"
              label="Donation size"
              value={form.size}
              onChange={(event) => update('size', event.target.value)}
              disabled={!options}
            >
              {(options?.size_presets ?? []).map((preset) => (
                <MenuItem key={preset.key} value={preset.key}>
                  {preset.label} · {preset.description}
                </MenuItem>
              ))}
            </Select>
            <FormFieldError errors={errors} field="size" />
          </FormControl>
          <TextField
            label="Quantity"
            type="number"
            inputProps={{ min: 1, max: options?.max_quantity ?? 10, step: 1 }}
            value={form.quantity}
            onChange={(event) => update('quantity', event.target.value)}
            error={Boolean(errors.quantity)}
            helperText={errors.quantity}
            required
            fullWidth
          />
        </Stack>
        <Alert severity="info">
          Estimated load: {estimatedWeight} kg · {formatVolumeM3(estimatedVolume)}
        </Alert>

        <Box>
          <Button component="label" variant="outlined" disabled={!options}>
            Choose photos
            <input
              hidden
              type="file"
              accept="image/jpeg,image/png,.jpg,.jpeg,.png"
              multiple
              onChange={(event) => updatePhotos(event.target.files)}
            />
          </Button>
          <Typography component="span" sx={{ ml: 1 }} color="text.secondary">
            {form.photos.length ? form.photos.map((file) => file.name).join(', ') : '1–3 JPG or PNG, up to 5 MB each'}
          </Typography>
          <FormFieldError errors={errors} field="photos" />
        </Box>

        <TextField
          label="Description (optional)"
          value={form.description}
          onChange={(event) => update('description', event.target.value)}
          error={Boolean(errors.description)}
          helperText={errors.description || `${form.description.length}/${options?.description_max_chars ?? 300}`}
          inputProps={{ maxLength: options?.description_max_chars ?? 300 }}
          multiline
          minRows={3}
          fullWidth
        />

        <Alert severity="warning">
          We cannot collect hazardous goods such as chemicals or gas bottles, or items over 30 kg. Please phone the centre about these items.
        </Alert>
        <Typography variant="body2" color="text.secondary">{PRIVACY_NOTICE}</Typography>
        <Button type="submit" variant="contained" size="large" disabled={isSubmitting || !options}>
          {isSubmitting ? 'Sending request…' : 'Submit pickup request'}
        </Button>
      </Box>
    </Container>
  );
}
