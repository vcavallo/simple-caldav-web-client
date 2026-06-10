# CalDAV Web Client

A self-hosted, single-user web calendar for viewing and editing events on a
Baikal (or any standard CalDAV) server. A FastAPI proxy holds the CalDAV
credentials and exposes a small JSON REST API; a React + FullCalendar SPA
renders month / week / agenda views.

```
[Browser] → REST/JSON → [FastAPI proxy] → CalDAV (HTTP+XML, Basic Auth) → [Baikal]
```

The browser never sees CalDAV credentials, and the proxy works around the fact
that CalDAV servers don't send permissive CORS headers.

## Features

- Month / week / agenda views (FullCalendar)
- Multiple calendars from one Baikal instance, color-coded, toggleable
- Create / edit / delete flat (non-recurring) events
- Recurring events are **displayed** (expanded per-occurrence) but not editable in v1
- ETag-based optimistic concurrency (`If-Match`) so concurrent edits are detected
- Keyboard-friendly: `M`/`W`/`A` views, `J`/`K` or arrows to navigate, `T` today, `N` new
- No cloud dependencies; meant to run on the local/Tailscale network

## Layout

```
backend/         FastAPI app + CalDAV/iCal logic (config.py, models.py, caldav_client.py, main.py)
backend/tests/   pytest suite (config, iCal conversion, API with a fake CalDAV client)
frontend/        React + Vite SPA (FullCalendar, React Query)
deploy/          systemd unit + NixOS module
shell.nix        Nix dev shell providing Python + all backend deps
config.example.yaml   copy to config.yaml (gitignored) and fill in
```

## Configuration

Copy the example and edit with your Baikal credentials:

```bash
cp config.example.yaml config.yaml
```

Each calendar's `id` is derived from its name (lowercased, alphanumerics only) —
e.g. `"Yellow House"` → `yellowhouse` — unless you set an explicit `id`.
Passwords may instead come from environment variables
`CALDAV_CAL_0_PASSWORD`, `CALDAV_CAL_1_PASSWORD`, … (index = list order), which
take precedence over the file.

## Development

This repo is developed on NixOS; `shell.nix` provides Python 3.11 with FastAPI,
caldav, icalendar, pytest and friends.

### Backend

```bash
# In the repo root:
nix-shell                       # drops you into a shell with all backend deps
python -m pytest                # run the test suite
uvicorn backend.main:app --reload --port 8080
```

Without Nix, use a virtualenv instead:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m pytest
uvicorn backend.main:app --reload --port 8080
```

The app reads `config.yaml` from the working directory by default; override with
the `CALDAV_CONFIG` environment variable.

### Frontend

```bash
cd frontend
npm install
npm run dev        # Vite dev server on :5173, proxies /api to :8080
npm test           # vitest unit tests
```

## Tests

- **Backend** (`pytest`): config loading + env overrides, the pure
  iCalendar↔JSON conversion and recurrence expansion, and every API endpoint
  (using an injected in-memory fake CalDAV client, so no server is required).
- **Frontend** (`vitest`): the `api.js` fetch wrapper and the pure event-form /
  FullCalendar helpers in `lib/events.js`.

## Production

Recommended: build the frontend and serve `frontend/dist/` as static files from
FastAPI — single process, single port. `backend/main.py` mounts `dist/` at `/`
automatically when it exists.

```bash
cd frontend && npm run build      # produces frontend/dist/
cd .. && uvicorn backend.main:app --host 0.0.0.0 --port 8080
```

Then reach it over Tailscale at `http://<host>:8080`.

### Deployment options

- **systemd** — see `deploy/caldav-webclient.service` (user unit). Put secrets in
  the `EnvironmentFile`.
- **NixOS** — see `deploy/nixos-module.nix` for a `services.caldav-webclient`
  module wrapping uvicorn.
- **Docker** — `docker compose up --build` (mounts `config.yaml` read-only).

## API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | `{ "ok": true }` liveness check |
| `GET` | `/api/calendars` | configured calendars (id, name, color — no credentials) |
| `GET` | `/api/events?start=&end=&calendars=` | merged events across calendars in range |
| `POST` | `/api/events` | create an event (returns id, url, etag) |
| `PUT` | `/api/events/{id}` | update an event (body includes url + etag) |
| `DELETE` | `/api/events/{id}` | delete an event (body includes url + etag) |

Errors return `{ "error": "message" }`; ETag conflicts return HTTP 412, auth
failures 502, unreachable server 503.

## Not in v1

Recurring-event editing, drag-and-drop reschedule, Google/Proton calendars,
multi-user, ICS import/export, cross-event search. See the project spec for the
full future-work list.
