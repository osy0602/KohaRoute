import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNzToday } from './useNzToday';
import { getNzToday } from '../api/health';

vi.mock('../api/health', () => ({ getNzToday: vi.fn() }));

describe('useNzToday', () => {
  beforeEach(() => vi.clearAllMocks());

  it('returns the New Zealand date supplied by the server', async () => {
    getNzToday.mockResolvedValue('2026-10-29');
    const { result } = renderHook(() => useNzToday());
    expect(result.current.nzToday).toBe('');
    await waitFor(() => expect(result.current.nzToday).toBe('2026-10-29'));
    expect(result.current.error).toBe('');
  });

  it('reports an error and recovers when retried', async () => {
    getNzToday.mockRejectedValueOnce(new Error('Cannot reach the server.'));
    getNzToday.mockResolvedValueOnce('2026-10-29');
    const { result } = renderHook(() => useNzToday());
    await waitFor(() => expect(result.current.error).toBe('Cannot reach the server.'));
    expect(result.current.nzToday).toBe('');

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.nzToday).toBe('2026-10-29'));
    expect(result.current.error).toBe('');
  });
});
