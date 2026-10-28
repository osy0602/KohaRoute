import { describe, expect, it } from 'vitest';
import {
  cubicMetresToLitres,
  formatCubicMetres,
  formatSizeLabel,
  formatVolumeM3,
} from './volume';

describe('cubicMetresToLitres', () => {
  it('converts whole and decimal cubic metres to whole litres', () => {
    expect(cubicMetresToLitres('3')).toBe(3000);
    expect(cubicMetresToLitres('0.8')).toBe(800);
    expect(cubicMetresToLitres('2.5')).toBe(2500);
    expect(cubicMetresToLitres('1.234')).toBe(1234);
    expect(cubicMetresToLitres(' 4 ')).toBe(4000);
  });

  it('is exact where float multiplication is not', () => {
    expect(cubicMetresToLitres('0.001')).toBe(1);
    expect(cubicMetresToLitres('1.1')).toBe(1100);
    expect(cubicMetresToLitres('4.35')).toBe(4350);
  });

  it('rejects zero, negative, empty, non-numeric and over-precise values', () => {
    for (const value of ['', '0', '0.000', '-1', 'abc', '1e3', '1.2345', '.5', '1,5', null]) {
      expect(cubicMetresToLitres(value)).toBeNull();
    }
  });
});

describe('formatCubicMetres', () => {
  it('shows at least two decimals and up to three', () => {
    expect(formatCubicMetres(3000)).toBe('3.00');
    expect(formatCubicMetres(2500)).toBe('2.50');
    expect(formatCubicMetres(3050)).toBe('3.05');
    expect(formatCubicMetres(1234)).toBe('1.234');
    expect(formatCubicMetres(1)).toBe('0.001');
  });

  it('round-trips with cubicMetresToLitres', () => {
    for (const litres of [1, 10, 850, 1234, 3000, 12000]) {
      expect(cubicMetresToLitres(formatCubicMetres(litres))).toBe(litres);
    }
  });
});

describe('formatVolumeM3', () => {
  it('labels volume in cubic metres for the size presets and totals', () => {
    expect(formatVolumeM3(20)).toBe('0.02 m³');
    expect(formatVolumeM3(60)).toBe('0.06 m³');
    expect(formatVolumeM3(150)).toBe('0.15 m³');
    expect(formatVolumeM3(730)).toBe('0.73 m³');
    expect(formatVolumeM3(0)).toBe('0.00 m³');
  });
});

describe('formatSizeLabel', () => {
  it('capitalises the stored preset key and tolerates a missing size', () => {
    expect(formatSizeLabel('medium')).toBe('Medium');
    expect(formatSizeLabel('Large')).toBe('Large');
    expect(formatSizeLabel('')).toBe('');
    expect(formatSizeLabel(undefined)).toBe('');
  });
});
