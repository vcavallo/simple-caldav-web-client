import React, { useState } from 'react'

// Inline detail popover positioned near the clicked event.
export default function EventPopover({ event, calendar, position, onEdit, onDelete, onClose }) {
  const [confirming, setConfirming] = useState(false)
  if (!event) return null

  const style = {
    top: Math.max(8, position?.y ?? 80),
    left: Math.min(position?.x ?? 80, window.innerWidth - 320),
  }

  const fmt = (s, allDay) => {
    if (!s) return ''
    if (allDay) return s.slice(0, 10)
    const d = new Date(s)
    return Number.isNaN(d.getTime()) ? s : d.toLocaleString()
  }

  return (
    <>
      <div className="popover-backdrop" onClick={onClose} />
      <div className="popover" style={style} role="dialog" aria-label="Event details">
        <div className="popover-head">
          <span className="swatch" style={{ backgroundColor: calendar?.color }} />
          <strong>{event.title}</strong>
          {event.recurring && (
            <span className="repeat" title="Recurring event">↻</span>
          )}
          <button className="icon-btn" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="popover-body">
          <div className="when">
            {fmt(event.start, event.allDay)}
            {event.end ? ` – ${fmt(event.end, event.allDay)}` : ''}
          </div>
          {event.location && <div className="loc">📍 {event.location}</div>}
          {event.description && <p className="desc">{event.description}</p>}
          <div className="cal-badge">{calendar?.name}</div>
        </div>

        <div className="popover-actions">
          {event.recurring ? (
            <span className="hint" title="Recurring events not yet editable">
              Recurring events not yet editable
            </span>
          ) : confirming ? (
            <>
              <span>Delete this event?</span>
              <button className="btn-danger" onClick={() => onDelete(event)}>
                Confirm
              </button>
              <button onClick={() => setConfirming(false)}>Cancel</button>
            </>
          ) : (
            <>
              <button onClick={() => onEdit(event)}>Edit</button>
              <button className="btn-danger" onClick={() => setConfirming(true)}>
                Delete
              </button>
            </>
          )}
        </div>
      </div>
    </>
  )
}
