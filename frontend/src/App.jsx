import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import CalendarView from './components/CalendarView'
import Sidebar from './components/Sidebar'
import EventPopover from './components/EventPopover'
import EventForm from './components/EventForm'
import { useCalendars } from './hooks/useCalendars'
import { useEventMutations } from './hooks/useEvents'
import api from './api'
import { blankEvent, toLocalInput, toDateInput } from './lib/events'

const HIDDEN_KEY = 'caldav.hiddenCalendars'

function loadHidden() {
  try {
    return JSON.parse(localStorage.getItem(HIDDEN_KEY)) || []
  } catch {
    return []
  }
}

export default function App() {
  const calendarRef = useRef(null)
  const { data: calendars = [] } = useCalendars()
  const [hidden, setHidden] = useState(loadHidden)
  const [popover, setPopover] = useState(null) // { event, position }
  const [form, setForm] = useState(null) // form state or null
  const [serverError, setServerError] = useState(null)

  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 30000,
    retry: false,
  })

  const refetchEvents = () => calendarRef.current?.getApi().refetchEvents()
  const onMutationError = (err) => setServerError(err.message)
  const { create, update, remove } = useEventMutations(onMutationError)

  const calendarsById = Object.fromEntries(calendars.map((c) => [c.id, c]))

  // --- persistence of hidden calendars ---
  useEffect(() => {
    localStorage.setItem(HIDDEN_KEY, JSON.stringify(hidden))
    refetchEvents()
  }, [hidden]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleCalendar = (id) =>
    setHidden((h) => (h.includes(id) ? h.filter((x) => x !== id) : [...h, id]))

  // --- form open helpers ---
  const openCreate = useCallback(
    (prefill = {}) => {
      setPopover(null)
      setServerError(null)
      setForm(
        blankEvent({
          calendar_id: prefill.calendar_id || calendars[0]?.id || '',
          ...prefill,
        }),
      )
    },
    [calendars],
  )

  const openEdit = (event) => {
    setPopover(null)
    setServerError(null)
    setForm({ ...blankEvent(), ...event })
  }

  // --- save / delete ---
  const handleSave = ({ id, payload }) => {
    setServerError(null)
    const onDone = { onSuccess: () => setForm(null) }
    if (id) {
      const original = form
      update.mutate(
        { id, payload: { ...payload, url: original.url, etag: original.etag } },
        onDone,
      )
    } else {
      create.mutate(payload, onDone)
    }
  }

  const handleDelete = (event) => {
    remove.mutate(
      { id: event.id, url: event.url, etag: event.etag },
      { onSuccess: () => setPopover(null) },
    )
  }

  // --- calendar interactions ---
  const onSelect = (arg) => {
    // Drag-select on week/day view: pre-fill start/end.
    openCreate({
      start: arg.allDay ? toDateInput(arg.start) : toLocalInput(arg.start),
      end: arg.allDay ? toDateInput(arg.end) : toLocalInput(arg.end),
      allDay: arg.allDay,
    })
  }

  const onDateClick = (arg) => {
    // Click a day on month view -> all-day prefill.
    openCreate({ start: toDateInput(arg.date), end: toDateInput(arg.date), allDay: true })
  }

  // --- keyboard shortcuts ---
  useEffect(() => {
    const handler = (e) => {
      if (e.target.matches('input, textarea, select')) return
      const apiCal = calendarRef.current?.getApi()
      if (!apiCal) return
      switch (e.key.toLowerCase()) {
        case 'm': apiCal.changeView('dayGridMonth'); break
        case 'w': apiCal.changeView('timeGridWeek'); break
        case 'a': apiCal.changeView('listWeek'); break
        case 't': apiCal.today(); break
        case 'j': case 'arrowleft': apiCal.prev(); break
        case 'k': case 'arrowright': apiCal.next(); break
        case 'n': openCreate(); break
        case 'escape': setForm(null); setPopover(null); break
        default: return
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [openCreate])

  const saving = create.isPending || update.isPending

  return (
    <div className="app">
      <Sidebar
        calendars={calendars}
        hidden={hidden}
        onToggle={toggleCalendar}
        onNew={() => openCreate()}
        health={health.isError ? false : health.data?.ok ?? null}
      />

      <main className="main">
        <CalendarView
          ref={calendarRef}
          calendars={calendars}
          hidden={hidden}
          onEventClick={(event, position) => setPopover({ event, position })}
          onDateClick={onDateClick}
          onSelect={onSelect}
        />
      </main>

      {popover && (
        <EventPopover
          event={popover.event}
          calendar={calendarsById[popover.event.calendar_id]}
          position={popover.position}
          onEdit={openEdit}
          onDelete={handleDelete}
          onClose={() => setPopover(null)}
        />
      )}

      {form && (
        <EventForm
          initial={form}
          calendars={calendars}
          onSave={handleSave}
          onClose={() => setForm(null)}
          saving={saving}
          serverError={serverError}
        />
      )}
    </div>
  )
}
