import { createTheme } from '@mui/material/styles';

/**
 * KohaRoute design tokens, tuned for projector presentation.
 *
 * Projectors wash out pale colours and thin lines, so this light theme uses near-black text on
 * white, saturated brand colours, 2px borders, larger type and chunky buttons. Every text/background
 * pair below meets WCAG AAA (7:1) or AA (4.5:1) contrast. The palette comes from Auckland itself:
 * harbour water, pounamu (greenstone), kowhai blossom and pohutukawa red.
 */
export const colors = {
  harbour: '#0B2530', // headings and body text
  pounamu: '#0B6B5D', // primary actions
  pounamuDark: '#074C42', // hover / pressed
  pounamuTint: '#DCF0EA', // soft highlight panels
  kowhai: '#F2B134', // accent
  pohutukawa: '#C62F1E', // errors and Missed
  mist: '#F3F7F6', // page background
  paper: '#FFFFFF', // cards and inputs
  line: '#9DB3AD', // visible on a projector; used for borders
  muted: '#3D5560', // secondary text, 8:1 on white
};

/** One strongly separated colour per booking status, used by chips, map pins and stop markers. */
export const statusColors = {
  pending: '#566A66',
  approved: '#C77F00',
  scheduled: '#1D5FB4',
  completed: '#16813F',
  missed: '#C62F1E',
  rejected: '#8E3A59',
};

/** Route lines need to stay distinct from the status colours above. */
export const routeColors = ['#1D5FB4', '#6B46C1', '#D9680B', '#0A7F94', '#B0246F', '#3B4656'];

const headingFont = '"Bricolage Grotesque", "Public Sans", system-ui, sans-serif';
const bodyFont = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif';

const buttonShadow = '0 3px 0 rgba(7, 76, 66, 0.35), 0 8px 16px rgba(11, 107, 93, 0.22)';

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
    background: { default: colors.mist, paper: colors.paper },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: bodyFont,
    // Larger than the Material default so text stays readable from the back of a room.
    fontSize: 16,
    h1: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1.12 },
    h4: { fontFamily: headingFont, fontWeight: 700, letterSpacing: '-0.015em', lineHeight: 1.15 },
    h5: { fontFamily: headingFont, fontWeight: 700 },
    h6: { fontFamily: headingFont, fontWeight: 700 },
    subtitle1: { fontWeight: 700 },
    subtitle2: { fontWeight: 700 },
    // Small labels read as quiet sentence-case text, not shouting capitals.
    overline: { textTransform: 'none', letterSpacing: 0, fontWeight: 700, fontSize: '1rem', lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 700, letterSpacing: 0, fontSize: '1rem' },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: colors.mist,
          // The "route line": a bold dashed path with stop dots along the top edge of every page.
          backgroundImage: `
                        radial-gradient(circle at 14px 5px, ${colors.kowhai} 0 5px, transparent 5.5px),
                        repeating-linear-gradient(90deg, ${colors.pounamu} 0 18px, transparent 18px 28px)`,
          backgroundSize: '280px 10px, 100% 5px',
          backgroundRepeat: 'repeat-x, repeat-x',
          backgroundPosition: '0 0, 0 2px',
          backgroundAttachment: 'scroll',
        },
        'a:focus-visible, button:focus-visible, [tabindex]:focus-visible': {
          outline: `3px solid ${colors.harbour}`,
          outlineOffset: 3,
        },
        '.leaflet-container': { fontFamily: bodyFont, borderRadius: 14, border: `2px solid ${colors.line}` },
        '@media (prefers-reduced-motion: reduce)': {
          '*': { animationDuration: '0.01ms !important', transitionDuration: '0.01ms !important' },
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: {
          borderRadius: 14,
          paddingInline: 24,
          minHeight: 48,
          transition: 'transform 120ms ease, box-shadow 120ms ease, background-color 120ms ease',
          '&:active': { transform: 'translateY(2px)' },
        },
        sizeSmall: { minHeight: 38, paddingInline: 16 },
        containedPrimary: {
          backgroundImage: `linear-gradient(180deg, #0F8272 0%, ${colors.pounamu} 100%)`,
          boxShadow: buttonShadow,
          '&:hover': { backgroundImage: 'none', backgroundColor: colors.pounamuDark, boxShadow: buttonShadow },
          '&:active': { boxShadow: '0 1px 0 rgba(7, 76, 66, 0.35)' },
          '&.Mui-disabled': { backgroundImage: 'none', backgroundColor: '#C5D2CE', color: '#4A5D58', boxShadow: 'none' },
        },
        containedError: { boxShadow: '0 3px 0 rgba(120, 25, 15, 0.35)' },
        outlined: {
          borderWidth: 2,
          borderColor: colors.pounamu,
          color: colors.pounamuDark,
          backgroundColor: colors.paper,
          '&:hover': { borderWidth: 2, borderColor: colors.pounamuDark, backgroundColor: colors.pounamuTint },
        },
        text: { '&:hover': { backgroundColor: colors.pounamuTint } },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: {
          border: `2px solid ${colors.line}`,
          borderRadius: 18,
          boxShadow: '0 6px 18px rgba(11, 37, 48, 0.08)',
        },
      },
    },
    MuiTextField: { defaultProps: { variant: 'outlined' } },
    MuiInputLabel: { styleOverrides: { root: { fontWeight: 600, color: colors.muted } } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: colors.paper,
          borderRadius: 12,
          '& .MuiOutlinedInput-notchedOutline': { borderColor: colors.line, borderWidth: 2 },
          '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: colors.pounamu },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: colors.pounamu, borderWidth: 3 },
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 700, borderRadius: 999, fontSize: '0.9rem' } },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 14, alignItems: 'center', fontSize: '1rem', fontWeight: 500 },
        standardInfo: {
          backgroundColor: colors.pounamuTint,
          color: colors.harbour,
          border: `2px solid ${colors.pounamu}`,
          '& .MuiAlert-icon': { color: colors.pounamu },
        },
        standardError: { border: `2px solid ${colors.pohutukawa}` },
        standardSuccess: { border: `2px solid ${statusColors.completed}` },
        standardWarning: { border: `2px solid ${statusColors.approved}` },
      },
    },
    MuiLink: {
      defaultProps: { underline: 'hover' },
      styleOverrides: { root: { fontWeight: 700, color: colors.pounamuDark } },
    },
    MuiDialog: { styleOverrides: { paper: { borderRadius: 20, border: `2px solid ${colors.line}` } } },
    MuiTableCell: {
      styleOverrides: {
        root: { borderBottom: `1px solid ${colors.line}`, fontSize: '1rem' },
        head: { fontWeight: 700, color: '#FFFFFF', backgroundColor: colors.harbour, borderBottom: 'none' },
      },
    },
    MuiTableRow: { styleOverrides: { root: { '&:hover': { backgroundColor: colors.pounamuTint } } } },
  },
});

export default theme;
