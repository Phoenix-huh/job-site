# ShieldDB — Job Scam Intelligence Dashboard

## Quick Start

```bash
# Backend (from backend/)
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (from frontend/, separate terminal)
npm install
npm run dev -- -p 3001
```

Frontend runs on **port 3001**, not 3000.

## Architecture

- **backend/** — FastAPI + SQLAlchemy. Entry point: `main.py`. All API routes are `/api/*`.
- **frontend/** — Next.js 16 + React 19 + **Tailwind v4** (despite README saying "zero Tailwind" — the code uses it). See `frontend/AGENTS.md` for Next.js version warnings.
- **Root scripts** — `inject_real_data.py` seeds the DB from the repo root; it adds `backend/` to `sys.path` to import from it.
- **Scoring engine** — `backend/scoring_engine.py` is a standalone module (no ML, all heuristic). It makes live HTTP calls to Clearbit and RDAP APIs.

## Database

- **Dev**: SQLite (`backend/sql_app.db`) — auto-created on first run.
- **Prod/Cloud**: PostgreSQL — set `DATABASE_URL` in `backend/.env`.
- `docker-compose.yml` provides a local Postgres 15 instance (`shield_user` / `shield_password` / `shield_db` on port 5432).
- `supabase_setup.sql` is a reference schema; actual tables are created by SQLAlchemy from `models.py`.

## Key Conventions & Gotchas

- **Auth**: JWT (HS256). First registered user is auto-promoted to admin (`is_admin=True`). Secret defaults to `"super-secret-key-for-job-site"` via `SECRET_KEY` env var.
- **Scraping**: Playwright runs **non-headless** to bypass bot detection. Requires a display/browser environment — will fail in headless CI without adjustments.
- **Tests**: No pytest. `test_db.py`, `test_api.py`, `test_scrapers.py`, `test_scrape.py` are standalone scripts run with `python <script>`, not a test framework.
- **API seed endpoint**: `GET /api/seed` wipes the DB and inserts 3 sample jobs. Destructive.
- **SSE**: `/api/notifications/stream` for real-time notifications; `/api/notifications/publish` to push events.
- **Windows**: `venv_win/` exists alongside `venv/` — use the appropriate one. `test_scrapers.py` reconfigures stdout to UTF-8 for Windows consoles.

## Commands

| Task | Command |
|---|---|
| Backend dev server | `uvicorn main:app --reload --host 0.0.0.0 --port 8000` (from `backend/`) |
| Frontend dev server | `npm run dev -- -p 3001` (from `frontend/`) |
| Scrape jobs (all roles) | `python daily_scrape.py` (from `backend/`, venv active) |
| Scrape specific roles | `python daily_scrape.py --roles "Data Analyst,Software Engineer" --max 10` |
| Seed DB with sample data | `python ../inject_real_data.py` (from `backend/`) or `GET /api/seed` |
| Frontend lint | `npm run lint` (from `frontend/`) |
| Frontend build | `npm run build` (from `frontend/`) |
