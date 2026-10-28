import { useEffect, useRef } from 'react';

/**
 * Call `callback` every `intervalMs` milliseconds while `enabled` is true.
 *
 * The timer is created and cleared inside one effect, so it is always stopped when the
 * component unmounts or `enabled`/`intervalMs` change, and timers can never pile up.
 * The newest `callback` is read from a ref, so the timer is not restarted on every render
 * and the callback never sees stale values such as an old selected date.
 * Ticks are skipped while the browser tab is hidden to avoid needless requests.
 *
 * @param {() => void} callback work to repeat, e.g. reload the live map
 * @param {number} intervalMs time between calls in milliseconds
 * @param {boolean} [enabled=true] set to false to pause polling
 */
export function usePolling(callback, intervalMs, enabled = true) {
  const latestCallback = useRef(callback);

  // Keep the ref pointing at the callback from the latest render.
  useEffect(() => {
    latestCallback.current = callback;
  });

  useEffect(() => {
    if (!enabled) return undefined;
    const timer = setInterval(() => {
      if (document.hidden) return;
      latestCallback.current();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs, enabled]);
}
