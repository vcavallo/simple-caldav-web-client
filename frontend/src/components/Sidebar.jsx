import React from 'react'

// Left panel: calendar list with color swatches and show/hide checkboxes.
export default function Sidebar({ calendars, hidden, onToggle, onNew, health }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>Calendar</h1>
        <button className="btn-primary" onClick={onNew} title="New event (N)">
          + New
        </button>
      </div>

      {health === false && (
        <div className="banner error">Cannot reach calendar server</div>
      )}

      <nav className="calendar-list">
        {calendars.map((cal) => (
          <label key={cal.id} className="calendar-item">
            <input
              type="checkbox"
              checked={!hidden.includes(cal.id)}
              onChange={() => onToggle(cal.id)}
            />
            <span className="swatch" style={{ backgroundColor: cal.color }} />
            <span className="calendar-name">{cal.name}</span>
          </label>
        ))}
      </nav>

      <div className="sidebar-footer">
        <p className="hint">
          <kbd>M</kbd> month · <kbd>W</kbd> week · <kbd>A</kbd> agenda
          <br />
          <kbd>J</kbd>/<kbd>K</kbd> nav · <kbd>T</kbd> today · <kbd>N</kbd> new
        </p>
      </div>
    </aside>
  )
}
