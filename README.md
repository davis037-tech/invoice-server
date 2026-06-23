# Ledger — backend

Flask + SQLAlchemy API for the invoice generator. This is the API only —
the frontend lives in a separate project/zip.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```
   (drop `--break-system-packages` if you're using a virtualenv)

2. Copy `.env.example` to `.env` and fill in real values:
   ```bash
   cp .env.example .env
   ```
   - `DATABASE_URL` — e.g. `sqlite:///app.db` for local dev
   - `SECRET_KEY` / `JWT_SECRET` — long random strings (32+ bytes recommended)
   - `FLW_SECRET_KEY` / `FLW_PUBLIC_KEY` / `FLW_WEBHOOK_SECRET` — from your
     Flutterwave dashboard (test keys work fine before KYC)
   - `FRONTEND_URL` — wherever you're serving the frontend from, e.g.
     `http://localhost:8080`. This must match exactly or CORS will block
     the frontend's requests.

3. Create the database tables:
   ```bash
   python3 -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

4. Run it:
   ```bash
   python3 run.py
   ```
   Runs on `http://localhost:5000` by default. All routes are under `/v1/...`.

## Routes

| Prefix | Purpose |
|---|---|
| `/v1/auth` | register, login, refresh |
| `/v1/clients` | client CRUD (requires auth) |
| `/v1/invoices` | invoice CRUD, send (requires auth) |
| `/v1/public` | public invoice view by token (no auth) |
| `/v1/billing` | Flutterwave webhook + payment status |

## Notes

- Multi-tenant: every client/invoice is scoped to the logged-in user's
  tenant. Confirmed isolated in testing — one tenant can't see another's data.
- Payments go through Flutterwave. The webhook handler always re-verifies
  the transaction server-side via Flutterwave's API rather than trusting
  the webhook payload directly — see `app/routes/billing.py`.
