import { Button, Container, Typography } from '@mui/material';
import { useAuth } from '../auth/AuthContext';

/** Temporary landing page for each role. Replaced by real screens in Parts 5 to 9. */
export default function StaffHomePlaceholder({ title }) {
  const { user, logout } = useAuth();
  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        {title}
      </Typography>
      <Typography sx={{ mb: 3 }}>
        Logged in as {user.full_name} ({user.role}).
      </Typography>
      <Button variant="outlined" onClick={logout}>
        Log out
      </Button>
    </Container>
  );
}
