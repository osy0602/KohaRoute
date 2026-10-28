import { createTheme } from "@mui/material/styles";

/**
 * KohaRoute design tokens.
 * Palette comes from Auckland itself: harbour water, pounamu (greenstone),
 * kowhai blossom and pohutukawa red. Status colours are shared with the maps.
 */
export const colors = {
    harbour: "#10243F",
    pounamu: "#0A7F6F",
    pounamuDark: "#066356",
    violet: "#5B3FD1",
    kowhai: "#FFC83D",
    coral: "#FF6B5E",
    pohutukawa: "#E5383B",
    mist: "#F2F6FF",
    line: "#D6DEF2",
    muted: "#4F6080",
};

/** One colour per booking status, used by chips, map pins and stop markers. */
export const statusColors = {
    pending: "#8E9AAF",
    approved: "#FFB703",
    scheduled: "#2F6FED",
    completed: "#1FA35C",
    missed: "#E5383B",
    rejected: "#B5446E",
};

/** Route lines need to stay distinct from the status colours above. */
export const routeColors = ["#2F6FED", "#8B5CF6", "#F97316", "#0891B2", "#DB2777", "#475569"];

const headingFont = '"Bricolage Grotesque", "Public Sans", system-ui, sans-serif';
const bodyFont = '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif';

const theme = createTheme({
    palette: {
        mode: "light",
        primary: { main: colors.pounamu, dark: colors.pounamuDark, contrastText: "#FFFFFF" },
        secondary: { main: colors.violet },
        warning: { main: colors.kowhai, contrastText: colors.harbour },
        error: { main: colors.pohutukawa },
        success: { main: statusColors.completed },
        info: { main: statusColors.scheduled },
        text: { primary: colors.harbour, secondary: colors.muted },
        divider: colors.line,
        background: { default: colors.mist, paper: "#FFFFFF" },
    },
    shape: { borderRadius: 10 },
    typography: {
        fontFamily: bodyFont,
        h1: { fontFamily: headingFont, fontWeight: 700, letterSpacing: "-0.02em" },
        h2: { fontFamily: headingFont, fontWeight: 700, letterSpacing: "-0.02em" },
        h3: { fontFamily: headingFont, fontWeight: 700, letterSpacing: "-0.02em", lineHeight: 1.12 },
        h4: { fontFamily: headingFont, fontWeight: 700, letterSpacing: "-0.015em", lineHeight: 1.15 },
        h5: { fontFamily: headingFont, fontWeight: 600 },
        h6: { fontFamily: headingFont, fontWeight: 600 },
        subtitle1: { fontWeight: 600 },
        subtitle2: { fontWeight: 600 },
        // Small labels read as quiet sentence-case text, not shouting capitals.
        overline: { textTransform: "none", letterSpacing: 0, fontWeight: 600, fontSize: "0.875rem", lineHeight: 1.5 },
        button: { textTransform: "none", fontWeight: 600, letterSpacing: 0 },
    },
    components: {
        MuiCssBaseline: {
            styleOverrides: {
                body: {
                    backgroundColor: colors.mist,
                    // A bright band behind every page header, a route line along the very top.
                    backgroundImage: `
                        radial-gradient(circle at 12px 3px, ${colors.harbour} 0 3px, transparent 3.5px),
                        repeating-linear-gradient(90deg, ${colors.harbour} 0 14px, transparent 14px 22px),
                        linear-gradient(115deg, #6EE7C8 0%, #FFD65A 45%, #FF8F70 100%)`,
                    backgroundSize: "240px 6px, 100% 3px, 100% 260px",
                    backgroundRepeat: "repeat-x, repeat-x, no-repeat",
                    backgroundPosition: "0 0, 0 1px, 0 0",
                },
                "a:focus-visible, button:focus-visible, [tabindex]:focus-visible": {
                    outline: `3px solid ${colors.violet}`,
                    outlineOffset: 2,
                },
                ".leaflet-container": { fontFamily: bodyFont, borderRadius: 12 },
                "@media (prefers-reduced-motion: reduce)": {
                    "*": { animationDuration: "0.01ms !important", transitionDuration: "0.01ms !important" },
                },
            },
        },
        MuiButton: {
            defaultProps: { disableElevation: true },
            styleOverrides: {
                root: { borderRadius: 10, paddingInline: 18 },
                containedPrimary: {
                    backgroundImage: `linear-gradient(135deg, ${colors.pounamu}, #0B6FB8)`,
                    boxShadow: "0 4px 12px rgba(10,127,111,0.35)",
                    "&:hover": { backgroundImage: `linear-gradient(135deg, ${colors.pounamuDark}, #095A96)` },
                    "&.Mui-disabled": { backgroundImage: "none" },
                },
                outlined: { borderColor: colors.line, color: colors.harbour, backgroundColor: "rgba(255,255,255,0.7)", "&:hover": { borderColor: colors.pounamu, backgroundColor: "rgba(10,127,111,0.10)" } },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: { backgroundImage: "none" },
                outlined: { borderColor: colors.line, borderRadius: 16, borderTop: `4px solid ${colors.violet}`, boxShadow: "0 8px 24px rgba(16,36,63,0.08)" },
            },
        },
        MuiTextField: { defaultProps: { variant: "outlined" } },
        MuiOutlinedInput: {
            styleOverrides: {
                root: {
                    backgroundColor: "#FFFFFF",
                    borderRadius: 10,
                    "& .MuiOutlinedInput-notchedOutline": { borderColor: colors.line },
                    "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: colors.pounamu },
                },
            },
        },
        MuiChip: { styleOverrides: { root: { fontWeight: 600, borderRadius: 999 } } },
        MuiAlert: {
            styleOverrides: {
                root: { borderRadius: 12, alignItems: "center" },
                standardInfo: { backgroundColor: "#DCEBFF", color: colors.harbour, "& .MuiAlert-icon": { color: statusColors.scheduled } },
            },
        },
        MuiLink: { defaultProps: { underline: "hover" }, styleOverrides: { root: { fontWeight: 600, color: colors.violet } } },
        MuiDialog: { styleOverrides: { paper: { borderRadius: 16 } } },
        MuiTableCell: { styleOverrides: { head: { fontWeight: 700, color: colors.harbour, backgroundColor: "#E4DEFB" } } },
    },
});

export default theme;
