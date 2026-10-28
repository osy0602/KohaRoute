import { useCallback, useEffect, useState } from 'react';
import { getNzToday } from '../api/health';

/**
 * Load today's date in New Zealand from the server.
 * "Today" must never come from the browser clock, because the browser may be in another
 * time zone; the server works it out in Pacific/Auckland time.
 * @returns {{nzToday: string, error: string, retry: () => void}} nzToday is "YYYY-MM-DD",
 *   or an empty string until it has loaded; retry reloads it after an error
 */
export function useNzToday() {
  const [nzToday, setNzToday] = useState('');
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true; // ignore a late reply after unmount or a newer retry
    setError('');
    getNzToday()
      .then((date) => {
        if (active) setNzToday(date);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((count) => count + 1), []);
  return { nzToday, error, retry };
}
