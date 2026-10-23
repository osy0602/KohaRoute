import { createTheme } from '@mui/material/styles';

// One place for colours and type, so every later screen looks like the same product.
// Harbour teal is the single brand colour; pohutukawa red is kept for errors only.
const theme = createTheme({
  palette: {
    primary: { main: '#1F6F78' },
    error: { main: '#B5413A' },
    success: { main: '#2F7A4D' },
    text: { primary: '#1B2B34', secondary: '#4A5B64' },
    background: { default: '#F2F5F5', paper: '#FFFFFF' },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"Segoe UI", system-ui, -apple-system, Roboto, "Helvetica Neue", Arial, sans-serif',
    h1: { fontSize: '2rem', fontWeight: 700, letterSpacing: '-0.01em' },
    h2: { fontSize: '1.125rem', fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
});

export default theme;
