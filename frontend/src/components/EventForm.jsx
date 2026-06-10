import React, { useState } from 'react'
import { validateEvent, toPayload } from '../lib/events'

// Slide-in create/edit panel. Uses a positioned div + backdrop (not <dialog>)
// to keep focus handling simple.
export default function EventForm({ initial, calendars, onSave, onClose, saving, serverError }) {
  const [form, setForm] = useState(initial)
  const [errors, setErrors] = useState([])
  const isEdit = !!form.id

  const set = (patch) => setForm((f) => ({ ...f, ...patch }))

  const handleAllDayToggle = (allDay) => {
    // Trim time components when switching to all-day, and vice versa.
    set({
      allDay,
      start: allDay ? form.start.slice(0, 10) : form.start,
      end: allDay ? form.end.slice(0, 10) : form.end,
    })
  }

  const submit = (e) => {
    e.preventDefault()
    const errs = validateEvent(form)
    setErrors(errs)
    if (errs.length === 0) onSave({ id: form.id, payload: toPayload(form), form })
  }

  return (
    <>
      <div className="panel-backdrop" onClick={onClose} />
      <form className="event-form" onSubmit={submit} aria-label="Event form">
        <header>
          <h2>{isEdit ? 'Edit event' : 'New event'}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        {(errors.length > 0 || serverError) && (
          <div className="banner error">
            {serverError || errors.join(' · ')}
          </div>
        )}

        <label>
          Title
          <input
            autoFocus
            value={form.title}
            onChange={(e) => set({ title: e.target.value })}
            placeholder="Title"
          />
        </label>

        <label>
          Calendar
          <select
            value={form.calendar_id}
            disabled={isEdit}
            onChange={(e) => set({ calendar_id: e.target.value })}
          >
            <option value="" disabled>
              Select a calendar
            </option>
            {calendars.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={form.allDay}
            onChange={(e) => handleAllDayToggle(e.target.checked)}
          />
          All day
        </label>

        <div className="time-row">
          <label>
            Start
            <input
              type={form.allDay ? 'date' : 'datetime-local'}
              value={form.start}
              onChange={(e) => set({ start: e.target.value })}
            />
          </label>
          <label>
            End
            <input
              type={form.allDay ? 'date' : 'datetime-local'}
              value={form.end}
              onChange={(e) => set({ end: e.target.value })}
            />
          </label>
        </div>

        <label>
          Location
          <input
            value={form.location}
            onChange={(e) => set({ location: e.target.value })}
          />
        </label>

        <label>
          Description
          <textarea
            rows={4}
            value={form.description}
            onChange={(e) => set({ description: e.target.value })}
          />
        </label>

        <footer>
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </footer>
      </form>
    </>
  )
}
