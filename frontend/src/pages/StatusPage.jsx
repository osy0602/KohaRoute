import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Typography,
} from '@mui/material';

import useHealth from '../hooks/useHealth.js';

/** One labelled line in the checklist. `ok` colours the value; `null` leaves it neutral. */
function CheckRow({ label, value, ok = null }) {
  const colour = ok === null ? 'text.primary' : ok ? 'success.main' : 'error.main';
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2} sx={{ py: 1.25 }}>
      <Typography color="text.secondary">{label}</Typography>
      <Typography sx={{ color: colour, fontWeight: 600, textAlign: 'right' }}>{value}</Typography>
    </Stack>
  );
}

function HealthReport({ data }) {
  return (
    <Stack divider={<Box sx={{ borderBottom: 1, borderColor: 'divider' }} />}>
      <CheckRow label="Backend" value="Running" ok />
      <CheckRow
        label="Database"
        value={data.database === 'ok' ? 'Connected' : 'Not available'}
        ok={data.database === 'ok'}
      />
      <CheckRow label="Today in New Zealand" value={data.nz_today} />
      <CheckRow label="Version" value={data.version} />
    </Stack>
  );
}

/** Part 0 start page: proves the frontend, the backend and the database are wired together. */
export default function StatusPage() {
  const { phase, data, retry } = useHealth();

  return (
    <Container maxWidth="sm" sx={{ py: { xs: 4, sm: 8 } }}>
      <Typography variant="h1" gutterBottom>
        KohaRoute
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 4 }}>
        Pickup planning for Auckland Community Centre.
      </Typography>

      <Paper variant="outlined" sx={{ p: { xs: 2, sm: 3 } }}>
        <Typography variant="h2" sx={{ mb: 1 }}>
          Setup check
        </Typography>

        {phase === 'loading' && (
          <Stack direction="row" spacing={2} alignItems="center" sx={{ py: 2 }}>
            <CircularProgress size={20} />
            <Typography>Checking the backend</Typography>
          </Stack>
        )}

        {phase === 'error' && (
          <Stack spacing={2} sx={{ pt: 1 }}>
            <Alert severity="error">
              Can&apos;t reach the backend. Start it from the backend folder with{' '}
              <code>uvicorn app.main:app --reload</code>, then try again.
            </Alert>
            <Button
              variant="contained"
              onClick={retry}
              sx={{ alignSelf: 'flex-start', minHeight: 44 }}
            >
              Try again
            </Button>
          </Stack>
        )}

        {phase === 'ready' && <HealthReport data={data} />}
      </Paper>
    </Container>
  );
}
