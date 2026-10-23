import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import StatusPage from './StatusPage.jsx';

const healthyReport = { status: 'ok', version: '0.1.0', database: 'ok', nz_today: '2026-10-15' };

function stubFetch(result) {
  vi.stubGlobal('fetch', vi.fn(result));
}

describe('StatusPage', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('shows the checklist when the backend is healthy', async () => {
    stubFetch(() => Promise.resolve({ ok: true, json: () => Promise.resolve(healthyReport) }));
    render(<StatusPage />);
    expect(await screen.findByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('2026-10-15')).toBeInTheDocument();
  });

  it('flags a database that is down', async () => {
    const degraded = { ...healthyReport, status: 'degraded', database: 'unavailable' };
    stubFetch(() => Promise.resolve({ ok: true, json: () => Promise.resolve(degraded) }));
    render(<StatusPage />);
    expect(await screen.findByText('Not available')).toBeInTheDocument();
  });

  it('offers Try again when the backend cannot be reached', async () => {
    stubFetch(() => Promise.reject(new TypeError('Failed to fetch')));
    render(<StatusPage />);
    expect(await screen.findByText(/Can't reach the backend/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });
});
