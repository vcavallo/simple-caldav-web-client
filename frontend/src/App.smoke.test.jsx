import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

// Regression guard: mounting <App/> must not trigger an infinite render loop
// (FullCalendar's events fn + a setState in the load-error callback once did).
describe('App', () => {
  it('mounts and renders the sidebar without a render loop', async () => {
    global.fetch = vi.fn().mockImplementation((url) => {
      const body = url.includes('/calendars')
        ? [{ id: 'personal', name: 'Personal', color: '#4A90D9' }]
        : url.includes('/events')
          ? { events: [], errors: [] }
          : { ok: true }
      return Promise.resolve({ ok: true, status: 200, json: async () => body })
    })

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    )

    // Sidebar header renders -> tree mounted, no thrown "Maximum update depth".
    expect(await screen.findByText('Calendar')).toBeInTheDocument()
    await waitFor(() =>
      expect(screen.getByText('Personal')).toBeInTheDocument(),
    )
  })
})
