// Thin fetch wrapper around the backend REST API.

const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 204) return null
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const message = (body && body.error) || `Request failed (${res.status})`
    const err = new Error(message)
    err.status = res.status
    throw err
  }
  return body
}

export const api = {
  health: () => request('/health'),

  getCalendars: () => request('/calendars'),

  getEvents: ({ start, end, calendars }) => {
    const params = new URLSearchParams({ start, end })
    if (calendars && calendars.length) {
      params.set('calendars', calendars.join(','))
    }
    return request(`/events?${params.toString()}`)
  },

  createEvent: (event) =>
    request('/events', { method: 'POST', body: JSON.stringify(event) }),

  updateEvent: (id, event) =>
    request(`/events/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(event),
    }),

  deleteEvent: (id, { url, etag }) =>
    request(`/events/${encodeURIComponent(id)}`, {
      method: 'DELETE',
      body: JSON.stringify({ url, etag }),
    }),
}

export default api
