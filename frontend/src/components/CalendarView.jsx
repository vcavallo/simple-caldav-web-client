import React, { forwardRef, useCallback } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import api from '../api'
import { toFullCalendarEvent } from '../lib/events'

// Wraps FullCalendar. The `events` prop is a function so FullCalendar drives
// the /api/events fetch for whatever range the current view needs.
const CalendarView = forwardRef(function CalendarView(
  { calendars, hidden, onEventClick, onDateClick, onSelect, onLoadErrors },
  ref,
) {
  // Stable across renders that don't change calendars/hidden, so FullCalendar
  // doesn't re-create its event source (and re-fetch) on every render. Without
  // this, the setState in onLoadErrors would re-render -> new function ->
  // re-fetch -> infinite loop.
  const fetchEvents = useCallback(
    (info, success, failure) => {
      const calendarsById = Object.fromEntries(calendars.map((c) => [c.id, c]))
      const visibleIds = calendars.map((c) => c.id).filter((id) => !hidden.includes(id))
      if (visibleIds.length === 0) {
        success([])
        onLoadErrors?.([])
        return
      }
      api
        .getEvents({
          start: info.startStr.slice(0, 19),
          end: info.endStr.slice(0, 19),
          calendars: visibleIds,
        })
        .then((data) => {
          // Backend returns { events, errors }; one bad calendar no longer
          // fails the whole fetch.
          const events = data.events || []
          success(events.map((e) => toFullCalendarEvent(e, calendarsById)))
          onLoadErrors?.(data.errors || [])
        })
        .catch(failure)
    },
    [calendars, hidden, onLoadErrors],
  )

  return (
    <div className="calendar-view">
      <FullCalendar
        ref={ref}
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,listWeek',
        }}
        views={{ listWeek: { duration: { weeks: 2 }, buttonText: 'agenda' } }}
        height="100%"
        nowIndicator
        selectable
        selectMirror
        dayMaxEvents
        events={fetchEvents}
        eventClick={(arg) => {
          arg.jsEvent.preventDefault()
          onEventClick(arg.event.extendedProps, {
            x: arg.jsEvent.clientX,
            y: arg.jsEvent.clientY,
          })
        }}
        dateClick={(arg) => onDateClick(arg)}
        select={(arg) => onSelect(arg)}
      />
    </div>
  )
})

export default CalendarView
