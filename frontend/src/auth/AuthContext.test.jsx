// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';
import { getToken, saveToken } from './tokenStorage';

const DRIVER = { id: 2, email: 'd@koha.nz', full_name: 'Driver', role: 'driver' };

/** Make fetch answer every call with the given status and JSON body. */
function stubFetch(status, body) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({ ok: status < 400, status, json: async () => body }),
  );
}

describe('AuthProvider', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
  });

  it('stores the token on login and forgets everything on logout', async () => {
    stubFetch(200, { access_token: 'tok', user: DRIVER });
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await act(() => result.current.login('d@koha.nz', 'pw'));
    expect(result.current.user).toEqual(DRIVER);
    expect(getToken()).toBe('tok');

    act(() => result.current.logout());
    expect(result.current.user).toBeNull();
    expect(getToken()).toBeNull();
  });

  it('drops an expired token when restoring the session', async () => {
    saveToken('old');
    stubFetch(401, { detail: 'Not logged in or session expired' });
    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isRestoring).toBe(false));
    expect(result.current.user).toBeNull();
    expect(getToken()).toBeNull();
  });
});
