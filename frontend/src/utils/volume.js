// Volume unit helpers. Admins work in cubic metres (m³), while the API, the database and
// the ORS Optimization API all use whole litres, so conversion happens in this one module.

/** Litres in one cubic metre. */
export const LITRES_PER_CUBIC_METRE = 1000;

/** 0.001 m³ is exactly 1 L, the smallest volume that is stored. */
const MAX_DECIMAL_PLACES = 3;

// Digits, optionally followed by a point and 1 to 3 decimal digits (e.g. "3", "3.5", "0.125").
const CUBIC_METRES_PATTERN = /^\d+(\.\d{1,3})?$/;

/**
 * Convert a cubic-metre value typed by the Admin into whole litres.
 * The text is converted digit by digit rather than multiplied as a float, so values such as
 * "0.001" or "1.1" never pick up rounding error.
 * @param {string|number} value cubic metres, e.g. "3.5"
 * @returns {number|null} whole litres, or null when the value is not a positive number
 *   with at most three decimal places
 */
export function cubicMetresToLitres(value) {
  const text = String(value ?? '').trim();
  if (!CUBIC_METRES_PATTERN.test(text)) return null;

  const [wholePart, fractionPart = ''] = text.split('.');
  const litres =
    Number(wholePart) * LITRES_PER_CUBIC_METRE +
    Number(fractionPart.padEnd(MAX_DECIMAL_PLACES, '0'));
  return litres > 0 ? litres : null;
}

/**
 * Format stored litres as cubic metres for display and for the edit form.
 * Shows at least two decimals ("3.00") and up to three when the litres need them ("1.234").
 * @param {number} litres whole litres
 * @returns {string} cubic metres, e.g. "3.00"
 */
export function formatCubicMetres(litres) {
  const text = (litres / LITRES_PER_CUBIC_METRE).toFixed(MAX_DECIMAL_PLACES);
  return text.endsWith('0') ? text.slice(0, -1) : text;
}

/**
 * Format stored litres as a labelled cubic-metre amount for screens, e.g. 60 L becomes "0.06 m³".
 * Every page uses this one function so volume is always shown in m³, never litres.
 * @param {number} litres whole litres
 * @returns {string} for example "0.06 m³"
 */
export function formatVolumeM3(litres) {
  return `${formatCubicMetres(litres)} m³`;
}

/**
 * Turn a stored size preset key into a label, e.g. "medium" becomes "Medium".
 * @param {string} size preset key saved with the booking
 * @returns {string} capitalised label, or an empty string when there is no size
 */
export function formatSizeLabel(size) {
  return size ? size.charAt(0).toUpperCase() + size.slice(1) : '';
}
