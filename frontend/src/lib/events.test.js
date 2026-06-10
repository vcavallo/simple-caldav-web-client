import { describe, it, expect } from 'vitest'
import {
  blankEvent,
  validateEvent,
  toPayload,
  toFullCalendarEvent,
} from './events'

describe('blankEvent', () => {
  it('produces an empty form with sensible defaults', () => {
    const e = blankEvent()
    expect(e.id).toBeNull()
    expect(e.title).toBe('')
    expect(e.allDay).toBe(false)
  })

  it('applies prefill values', () => {
    const e = blankEvent({ start: '2025-09-16T10:00', end: '2025-09-16T11:00', calendar_id: 'personal' })
    expect(e.start).toBe('2025-09-16T10:00')
    expect(e.calendar_id).toBe('personal')
  })
})

describe('validateEvent', () => {
  const valid = {
    title: 'Meeting',
    calendar_id: 'personal',
    start: '2025-09-16T10:00',
    end: '2025-09-16T11:00',
  }

  it('passes a valid form', () => {
    expect(validateEvent(valid)).toEqual([])
  })

  it('requires a title', () => {
    expect(validateEvent({ ...valid, title: '   ' })).toContain('Title is required')
  })

  it('requires a calendar', () => {
    expect(validateEvent({ ...valid, calendar_id: '' })).toContain('Calendar is required')
  })

  it('rejects end before start', () => {
    expect(validateEvent({ ...valid, end: '2025-09-16T09:00' })).toContain(
      'End must be after start',
    )
  })
})

describe('toPayload', () => {
  it('trims title and includes only backend fields', () => {
    const payload = toPayload({
      calendar_id: 'personal',
      title: '  Hi  ',
      start: 's',
      end: 'e',
      allDay: true,
      location: 'here',
      description: 'd',
      url: '/should-not-appear',
      etag: '"x"',
    })
    expect(payload).toEqual({
      calendar_id: 'personal',
      title: 'Hi',
      start: 's',
      end: 'e',
      allDay: true,
      location: 'here',
      description: 'd',
    })
    expect(payload.url).toBeUndefined()
  })
})

describe('toFullCalendarEvent', () => {
  const calendarsById = { personal: { id: 'personal', color: '#4A90D9' } }

  it('colors events by calendar', () => {
    const fc = toFullCalendarEvent(
      { id: '1', calendar_id: 'personal', title: 'X', start: 's', end: 'e', allDay: false },
      calendarsById,
    )
    expect(fc.backgroundColor).toBe('#4A90D9')
    expect(fc.editable).toBe(true)
  })

  it('marks recurring events as not editable', () => {
    const fc = toFullCalendarEvent(
      { id: '1_2025', calendar_id: 'personal', title: 'X', start: 's', end: 'e', recurring: true },
      calendarsById,
    )
    expect(fc.editable).toBe(false)
  })

  it('preserves the raw event in extendedProps', () => {
    const raw = { id: '1', calendar_id: 'personal', title: 'X', start: 's', end: 'e', etag: '"e"' }
    const fc = toFullCalendarEvent(raw, calendarsById)
    expect(fc.extendedProps.etag).toBe('"e"')
  })
})
