import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { CssBaseline, ThemeProvider } from '@mui/material';
import theme from './theme';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import BookPickup from './pages/BookPickup';
import TrackBooking from './pages/TrackBooking';
import { staffRoutes } from './routes/staffRoutes';
import ScreenBackdrop from './components/ScreenBackdrop';

/** Screens that keep the waves but drop the route line, pins and glows. */
const WAVES_ONLY_SCREENS = ['/book', '/admin/routes'];

/** Public and login screens get the full illustration; busy staff screens a fainter one. */
function Backdrop() {
  const { pathname } = useLocation();
  const wavesOnly = WAVES_ONLY_SCREENS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
  const isStaffWorkScreen = pathname.startsWith('/admin') || pathname.startsWith('/driver');
  return <ScreenBackdrop variant={isStaffWorkScreen ? 'subtle' : 'hero'} wavesOnly={wavesOnly} />;
}

function App() {
  return (
    <AuthProvider>
      <Backdrop />
      <Routes>
        <Route path="/" element={<Navigate to="/book" replace />} />
        <Route path="/book" element={<BookPickup />} />
        <Route path="/track" element={<TrackBooking />} />
        {staffRoutes}
        <Route path="*" element={<Navigate to="/book" replace />} />
      </Routes>
    </AuthProvider>
  );
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
);
