import { Link as RouterLink, Route, Routes } from 'react-router-dom';
import { Container, Link, Typography } from '@mui/material';

import StatusPage from './pages/StatusPage.jsx';

function NotFoundPage() {
  return (
    <Container maxWidth="sm" sx={{ py: 6 }}>
      <Typography variant="h1" gutterBottom>
        Page not found
      </Typography>
      <Link component={RouterLink} to="/">
        Back to the start page
      </Link>
    </Container>
  );
}

/** Route table for the whole app. Later parts add one <Route> per screen here. */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<StatusPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
