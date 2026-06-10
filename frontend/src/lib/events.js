// Pure helpers for event form state and FullCalendar conversion.

// Round a Date to the local "YYYY-MM-DDTHH:mm" string an <input type=datetime-local> wants.
export function toLocalInput(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

export function toDateInput(date) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

// A blank event form, optionally pre-filled from a calendar click.
export function blankEvent(prefill = {}) {
  return {
    id: null,
    calendar_id: prefill.calendar_id || '',
    title: '',
    start: prefill.start || '',
    end: prefill.end || '',
    allDay: prefill.allDay || false,
    location: '',
    description: '',
    url: '',
    etag: '',
    recurring: false,
  }
}

// Returns an array of validation error strings (empty = valid).
export function validateEvent(form) {
  const errors = []
  if (!form.title || !form.title.trim()) errors.push('Title is required')
  if (!form.calendar_id) errors.push('Calendar is required')
  if (!form.start) errors.push('Start is required')
  if (!form.end) errors.push('End is required')
  if (form.start && form.end && form.end < form.start) {
    errors.push('End must be after start')
  }
  return errors
}

// Build the JSON payload the backend expects from a form.
export function toPayload(form) {
  return {
    calendar_id: form.calendar_id,
    title: form.title.trim(),
    start: form.start,
    end: form.end,
    allDay: !!form.allDay,
    location: form.location || '',
    description: form.description || '',
  }
}

// Convert a backend event into a FullCalendar event input.
export function toFullCalendarEvent(event, calendarsById = {}) {
  const cal = calendarsById[event.calendar_id]
  return {
    id: event.id,
    title: event.title,
    start: event.start,
    end: event.end,
    allDay: event.allDay,
    backgroundColor: cal ? cal.color : undefined,
    borderColor: cal ? cal.color : undefined,
    editable: !event.recurring,
    extendedProps: { ...event },
  }
}
