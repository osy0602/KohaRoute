import { createTheme } from '@mui/material/styles';

/**
 * KohaRoute design tokens.
 * Palette comes from Auckland itself: harbour water, pounamu (greenstone),
 * kowhai blossom and pohutukawa red. Status colours are shared with the maps.
 */
export const colors = {
  harbour: '#12343B',
  pounamu: '#1F7A6B',
  pounamuDark: '#165A4F',
  kowhai: '#F2B134',
  pohutukawa: '#C8432F',
  mist: '#EEF3F1',
  line: '#D3DEDA',
  muted: '#5B706C',
};

/** One colour per booking status, used by chips, map pins and stop markers. */
export const statusColors = {
  pending: '#7A8B88',
  approved: '#E0A21A',
  scheduled: '#2B6CB0',
  completed: '#2E9E5B',
  missed: '#C8432F',
  rejected: '#8A4B5C',
};

/** Route lines need to stay distinct from the status colours above. */
export const routeColors = ['#2B6CB0', '#7B5EA7', '#D9822B', '#0E8FA3', '#B83280', '#4A5568'];

const headingFont = '"Bricolage Grotesque", "Public Sans", system-ui, sans-serif';
const bodyFont = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: colors.pounamu, dark: colors.pounamuDark, contrastText: '#FFFFFF' },
    secondary: { main: colors.harbour },
    warning: { main: colors.kowhai, contrastText: colors.harbour },
    error: { main: colors.pohutukawa },
    success: { main: statusColors.completed },
    info: { main: statusColors.scheduled },
    text: { primary: colors.harbour, secondary: colors.muted },
    divider: colors.line,
    background: { default: colors.mist, paper: '#FFFFFF' },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: bodyFont,
    h1: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.12 },
    h4: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.015em', lineHeight: 1.15 },
    h5: { fontFamily: headingFont, fontWeight: 600 },
    h6: { fontFamily: headingFont, fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    // Small labels read as quiet sentence-case text, not shouting capitals.
    overline: { textTransform: 'none', letterSpacing: 0, fontWeight: 600, fontSize: '0.875rem', lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 600, letterSpacing: 0 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: colors.mist,
          // The "route line": a dashed path with stop dots along the top edge of every page.
          backgroundImage: `
                        radial-gradient(circle at 12px 3px, ${colors.kowhai} 0 3px, transparent 3.5px),
                        repeating-linear-gradient(90deg, ${colors.pounamu} 0 14px, transparent 14px 22px)`,
          backgroundSize: '240px 6px, 100% 3px',
          backgroundRepeat: 'repeat-x, repeat-x',
          backgroundPosition: '0 0, 0 1px',
          backgroundAttachment: 'scroll',
        },
        'a:focus-visible, button:focus-visible, [tabindex]:focus-visible': {
          outline: `3px solid ${colors.kowhai}`,
          outlineOffset: 2,
        },
        '.leaflet-container': { fontFamily: bodyFont, borderRadius: 12 },
        '@media (prefers-reduced-motion: reduce)': {
          '*': { animationDuration: '0.01ms !important', transitionDuration: '0.01ms !important' },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 10, paddingInline: 18 },
        containedPrimary: { '&:hover': { backgroundColor: colors.pounamuDark } },
        outlined: { borderColor: colors.line, '&:hover': { borderColor: colors.pounamu, backgroundColor: 'rgba(31,122,107,0.06)' } },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { borderColor: colors.line, borderRadius: 14 },
      },
    },
    MuiTextField: { defaultProps: { variant: 'outlined' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          borderRadius: 10,
          '& .MuiOutlinedInput-notchedOutline': { borderColor: colors.line },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: colors.pounamu },
        },
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 600, borderRadius: 999 } } },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 12, alignItems: 'center' },
        standardInfo: { backgroundColor: '#E3EFEC', color: colors.harbour, '& .MuiAlert-icon': { color: colors.pounamu } },
      },
    },
    MuiLink: { defaultProps: { underline: 'hover' }, styleOverrides: { root: { fontWeight: 600, color: colors.pounamu } } },
    MuiDialog: { styleOverrides: { paper: { borderRadius: 16 } } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 700, color: colors.harbour, backgroundColor: '#E3EDEA' } } },
  },
});

export default theme;
