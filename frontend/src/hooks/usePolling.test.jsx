import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePolling } from './usePolling';

function setTabHidden(hidden) {
  Object.defineProperty(document, 'hidden', { value: hidden, configurable: true });
}

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setTabHidden(false);
  });
  afterEach(() => {
    vi.useRealTimers();
    setTabHidden(false);
  });

  it('calls the callback once per interval', () => {
    const callback = vi.fn();
    renderHook(() => usePolling(callback, 60_000));
    vi.advanceTimersByTime(59_999);
    expect(callback).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(callback).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(120_000);
    expect(callback).toHaveBeenCalledTimes(3);
  });

  it('uses the newest callback without restarting or stacking timers', () => {
    const first = vi.fn();
    const second = vi.fn();
    const { rerender } = renderHook(({ callback }) => usePolling(callback, 60_000), {
      initialProps: { callback: first },
    });
    rerender({ callback: second });
    rerender({ callback: second });
    vi.advanceTimersByTime(60_000);
    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);
  });

  it('stops when unmounted or disabled', () => {
    const callback = vi.fn();
    const { rerender, unmount } = renderHook(
      ({ enabled }) => usePolling(callback, 60_000, enabled),
      { initialProps: { enabled: true } },
    );
    rerender({ enabled: false });
    expect(vi.getTimerCount()).toBe(0);
    rerender({ enabled: true });
    expect(vi.getTimerCount()).toBe(1);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    vi.advanceTimersByTime(180_000);
    expect(callback).not.toHaveBeenCalled();
  });

  it('skips a tick while the browser tab is hidden', () => {
    const callback = vi.fn();
    renderHook(() => usePolling(callback, 60_000));
    setTabHidden(true);
    vi.advanceTimersByTime(60_000);
    expect(callback).not.toHaveBeenCalled();
    setTabHidden(false);
    vi.advanceTimersByTime(60_000);
    expect(callback).toHaveBeenCalledTimes(1);
  });
});
