import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from './api'

function mockFetch(status, body) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })
}

describe('api', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('getCalendars hits /api/calendars', async () => {
    mockFetch(200, [{ id: 'personal', name: 'Personal', color: '#fff' }])
    const cals = await api.getCalendars()
    expect(global.fetch).toHaveBeenCalledWith('/api/calendars', expect.any(Object))
    expect(cals[0].id).toBe('personal')
  })

  it('getEvents builds a query string with date range', async () => {
    mockFetch(200, [])
    await api.getEvents({ start: '2025-09-01T00:00:00', end: '2025-09-30T00:00:00' })
    const url = global.fetch.mock.calls[0][0]
    expect(url).toContain('/api/events?')
    expect(url).toContain('start=2025-09-01T00%3A00%3A00')
    expect(url).toContain('end=2025-09-30T00%3A00%3A00')
  })

  it('getEvents includes calendars filter when provided', async () => {
    mockFetch(200, [])
    await api.getEvents({ start: 'a', end: 'b', calendars: ['personal', 'work'] })
    const url = global.fetch.mock.calls[0][0]
    expect(url).toContain('calendars=personal%2Cwork')
  })

  it('createEvent POSTs JSON body', async () => {
    mockFetch(201, { id: 'x' })
    await api.createEvent({ title: 'Hi' })
    const [, opts] = global.fetch.mock.calls[0]
    expect(opts.method).toBe('POST')
    expect(JSON.parse(opts.body)).toEqual({ title: 'Hi' })
  })

  it('deleteEvent returns null on 204', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 204 })
    const res = await api.deleteEvent('x', { url: '/u', etag: '"e"' })
    expect(res).toBeNull()
  })

  it('throws with server error message on non-ok response', async () => {
    mockFetch(412, { error: 'Event was modified elsewhere' })
    await expect(api.updateEvent('x', {})).rejects.toThrow('Event was modified elsewhere')
  })

  it('attaches status code to thrown error', async () => {
    mockFetch(404, { error: 'nope' })
    try {
      await api.updateEvent('x', {})
      throw new Error('should have thrown')
    } catch (e) {
      expect(e.status).toBe(404)
    }
  })
})
