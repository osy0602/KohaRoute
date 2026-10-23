import { useCallback, useEffect, useState } from 'react';

import { fetchHealth } from '../api/health.js';

/**
 * Load the backend health report and expose a retry function.
 *
 * @returns {{phase: 'loading'|'ready'|'error', data: object|null, retry: () => void}}
 */
export default function useHealth() {
  const [state, setState] = useState({ phase: 'loading', data: null });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ phase: 'loading', data: null });
    fetchHealth(controller.signal)
      .then((data) => setState({ phase: 'ready', data }))
      .catch((error) => {
        // An aborted request means the page went away or a retry started; not a real failure.
        if (error.name !== 'AbortError') setState({ phase: 'error', data: null });
      });
    return () => controller.abort();
  }, [attempt]);

  const retry = useCallback(() => setAttempt((count) => count + 1), []);
  return { ...state, retry };
}
