import { useState } from 'react';
import { Alert, Box, Button, Container, TextField, Typography } from '@mui/material';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { homePathForRole } from '../auth/roleHome';

/** Check both fields are filled in; returns messages keyed by field name. */
function validate(email, password) {
  const errors = {};
  if (!email.trim()) errors.email = 'Enter your email.';
  if (!password) errors.password = 'Enter your password.';
  return errors;
}

/** The staff login form shared by Admin and drivers (US-01). */
export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (user) return <Navigate to={homePathForRole(user.role)} replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    const errors = validate(email, password);
    setFieldErrors(errors);
    setServerError('');
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    try {
      const loggedIn = await login(email.trim(), password);
      // Return to the page that needed a login, if it suits this user's role.
      const wanted = location.state?.from?.pathname;
      const home = homePathForRole(loggedIn.role);
      navigate(wanted?.startsWith(home) ? wanted : home, { replace: true });
    } catch (error) {
      setServerError(error.message);
      setIsSubmitting(false);
    }
  }

  return (
    <Container maxWidth="xs" sx={{ py: { xs: 4, sm: 10 } }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Staff log in
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>
        KohaRoute for Te Manawa Community Centre admins and drivers.
      </Typography>

      <Box component="form" noValidate onSubmit={handleSubmit} sx={{ display: 'grid', gap: 2 }}>
        {serverError && <Alert severity="error">{serverError}</Alert>}
        <TextField
          label="Email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={Boolean(fieldErrors.email)}
          helperText={fieldErrors.email}
          fullWidth
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={Boolean(fieldErrors.password)}
          helperText={fieldErrors.password}
          fullWidth
        />
        <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </Button>
      </Box>
    </Container>
  );
}
