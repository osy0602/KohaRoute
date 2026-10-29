import { Box } from '@mui/material';

/**
 * Decorative page background: soft harbour waves, a dashed pickup route with stop pins and two
 * faint glows. It is drawn behind the page, ignores the mouse, and uses very light tints so text,
 * forms and maps stay fully readable when shown on a projector.
 *
 * @param {object} props
 * @param {'hero'|'subtle'} [props.variant] `hero` for public and login screens, `subtle` (about half
 *   as strong) for the busy Admin and driver screens.
 * @param {boolean} [props.wavesOnly] Draw only the waves, leaving out the route line, pins and
 *   glows (used on the booking form and the route planner).
 * @returns {JSX.Element} A fixed, full-screen, non-interactive illustration.
 */
export default function ScreenBackdrop({ variant = 'hero', wavesOnly = false }) {
  return (
    <Box
      aria-hidden
      sx={{
        position: 'fixed',
        inset: 0,
        zIndex: -1,
        pointerEvents: 'none',
        opacity: variant === 'subtle' ? 0.5 : 1,
        overflow: 'hidden',
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMax slice"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <radialGradient id="kr-glow-gold" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#F2B134" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#F2B134" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="kr-glow-green" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#0B6B5D" stopOpacity="0.14" />
            <stop offset="100%" stopColor="#0B6B5D" stopOpacity="0" />
          </radialGradient>
        </defs>

        {!wavesOnly && (
          <>
            <circle cx="1300" cy="90" r="340" fill="url(#kr-glow-gold)" />
            <circle cx="40" cy="60" r="300" fill="url(#kr-glow-green)" />
          </>
        )}

        <path
          d="M0 640 C 240 580 420 700 700 650 C 980 600 1180 520 1440 590 L1440 900 L0 900 Z"
          fill="#0B6B5D"
          fillOpacity="0.09"
        />
        <path
          d="M0 720 C 300 660 520 780 820 730 C 1100 685 1250 640 1440 690 L1440 900 L0 900 Z"
          fill="#1D5FB4"
          fillOpacity="0.07"
        />
        <path
          d="M0 800 C 260 750 520 850 840 810 C 1120 775 1280 740 1440 780 L1440 900 L0 900 Z"
          fill="#0B6B5D"
          fillOpacity="0.14"
        />

        {!wavesOnly && (
          <>
            <path
              d="M120 780 C 300 650 420 720 560 620 S 860 540 1000 640 S 1260 580 1340 480"
              fill="none"
              stroke="#0B6B5D"
              strokeOpacity="0.4"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="14 12"
            />
            {[
              [120, 780],
              [560, 620],
              [1000, 640],
            ].map(([x, y]) => (
              <circle key={x} cx={x} cy={y} r="10" fill="#F2B134" stroke="#FFFFFF" strokeWidth="3" />
            ))}
            {/* Destination pin */}
            <path
              d="M1340 430 C 1316 430 1300 448 1300 470 C 1300 496 1340 530 1340 530 C 1340 530 1380 496 1380 470 C 1380 448 1364 430 1340 430 Z"
              fill="#0B6B5D"
              fillOpacity="0.55"
            />
            <circle cx="1340" cy="468" r="13" fill="#FFFFFF" fillOpacity="0.9" />
          </>
        )}
      </svg>
    </Box>
  );
}
