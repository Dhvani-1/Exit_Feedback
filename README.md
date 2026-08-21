# Employee Exit Feedback Automation System - Phase 1 & Phase 2

Phase 1 provides HR Employee Management, secure authentication, and authoritative 3-calendar-month feedback due date calculation.

Phase 2 builds a persistent, reliable **Automated Email System** on top of Phase 1. It automatically dispatches employee exit feedback emails when an employee reaches their calculated `feedback_due_date`, supported by a standalone background worker engine, atomic job claiming, failure retries, stuck job lease recovery, and HR controls for Send Now, Reschedule, Cancel, and Retry.

---

## 1. System Architecture

```text
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── config.py         # Settings for DB, JWT, & Email Provider
│   │   ├── main.py           # FastAPI Entrypoint & Worker Health Check
│   │   ├── database/         # SQLAlchemy Engine & Connection Session
│   │   ├── models/           # User, Employee, EmailJob, EmailTemplate, SystemSetting
│   │   ├── routes/           # Auth, Employees, Email Jobs, Settings, Dashboard
│   │   ├── schemas/          # Pydantic Schemas & Timezone Validations
│   │   ├── services/         # Date Calculator, Email Service, Jinja2 Sandbox, Worker Engine, Backfill
│   │   └── utils/            # Security & Error Envelopes
│   ├── migrations/           # Alembic Database Migrations (001_initial, 002_email_system)
│   ├── tests/                # Pytest Test Suite (32 Passed Integration & Unit Tests)
│   ├── create_admin.py       # Admin Seeding Script
│   ├── run_worker.py         # Standalone Background Worker Process
│   └── requirements.txt
├── frontend/                 # React 18 + Vite + Tailwind CSS Frontend
│   ├── src/
│   │   ├── components/       # Badges, Modals, History Tables, Layout
│   │   ├── pages/            # Login, Dashboard, Directory, Create, Edit, Details
│   │   └── services/         # Axios API Client withCredentials
│   ├── package.json
│   └── vite.config.js
└── README.md
```

---

## 2. Key Phase 2 Features & Guarantees

1. **Delivery Guarantee**:
   - Designed for **at-least-once delivery + application-level duplicate prevention + idempotency keys** (`EXIT_FEEDBACK_INITIAL:<employee_id>`).
2. **Database-Level Unique Constraint**:
   - `email_jobs` table enforces `UNIQUE(employee_id, email_type)` at DB level.
   - Idempotent backfill process uses `ON CONFLICT DO NOTHING` to safely convert existing Phase 1 records into scheduled email jobs.
3. **Atomic Job Claiming**:
   - Shared atomic query: `UPDATE email_jobs SET status = 'PROCESSING', processing_started_at = UTC_NOW() WHERE id = :id AND status = 'SCHEDULED'`.
   - Prevents race conditions between background workers and manual HR `Send Now` actions.
4. **Failure Classification & Exponential Retry**:
   - **Retryable Errors** (e.g. SMTP connection timeout, 5xx server error): Reuses job record, increments `attempt_count`, reschedules with exponential backoff (5m, 10m, 20m).
   - **Non-retryable Errors** (e.g. invalid recipient address, auth failure): Immediately marks `FAILED` with sanitized error log.
5. **Stuck `PROCESSING` Lease Recovery**:
   - Jobs in `PROCESSING` for > 15 minutes are checked via worker lease expiry (`processing_started_at`). Reset to `SCHEDULED` if attempts remain, else marked `FAILED`.
6. **Timezone-Aware UTC Timestamp Conversion**:
   - `scheduled_at` is converted from Phase 1 calendar `feedback_due_date` + `email_send_hour` (default 09:00 AM) in configured timezone (default `Asia/Kolkata`) into timezone-aware UTC datetime.
7. **Email Provider Modes (`EMAIL_MODE`)**:
   - `EMAIL_MODE=console` (default): Logs simulated delivery details with `DELIVERY_MODE=SIMULATED` for safe local dev and automated testing.
   - `EMAIL_MODE=smtp`: Transmits HTML MIME emails over TLS-secured SMTP connection.
8. **HR Management & Audit History**:
   - **Send Now**: Immediate atomic claim & dispatch.
   - **Reschedule**: Updates `scheduled_at` for unsent `SCHEDULED` jobs.
   - **Cancel Email**: Soft cancels unsent email job.
   - **Manual Retry**: Resets a `FAILED` job back to `SCHEDULED`.
   - **Audit History**: Complete timeline table of email jobs on Employee Details page.

---

## 3. Environment Configuration

`backend/.env`:

```env
DATABASE_URL=sqlite:///./exit_feedback.db
# For production PostgreSQL:
# DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/exit_feedback

SECRET_KEY=dev_secret_key_exit_feedback_automation_2026_super_secure_32bytes
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Phase 2 Email Provider Settings
# Phase 2 & Test Email Provider Settings
EMAIL_MODE=console
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=True

# Current TEST Sender Address (Temporary & Replaceable via .env or Settings UI)
EMAIL_FROM=dhvani111005@gmail.com
EMAIL_FROM_NAME=HR Department

# Phase 2 System Settings Defaults
DEFAULT_TIMEZONE=Asia/Kolkata
DEFAULT_SEND_HOUR=9
DEFAULT_WEEKEND_BEHAVIOR=SEND_ON_DUE_DATE
```

> [!NOTE]
> **Current TEST Sender Notice**:
> **Current TEST sender**: `dhvani111005@gmail.com`
> This address is temporary and must be replaceable through environment configuration (`EMAIL_FROM` in `backend/.env`) or via the Settings UI (`/settings`) without modifying application source code.

---

## 4. Quickstart Setup (Windows PowerShell)

### Step 4.1: Backend Migrations & Seeding

```powershell
cd backend

# Install Python dependencies
python -m pip install -r requirements.txt

# Run Alembic migrations (creates email_jobs, email_templates, system_settings)
python -m alembic upgrade head

# Seed admin user
python create_admin.py --email hr@company.com --password AdminPass123! --name "HR Administrator" --role ADMIN
```

### Step 4.2: Start Standalone Background Worker

Open a new PowerShell terminal:

```powershell
cd backend
python run_worker.py
```

### Step 4.3: Start FastAPI Backend Server

Open another PowerShell terminal:

```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Step 4.4: Start Frontend Dev Server

Open another PowerShell terminal:

```powershell
cd frontend
cmd /c "npm install"
cmd /c "npm run dev"
```

Open your browser at `http://localhost:5173`.
Log in with credentials: `hr@company.com` / `AdminPass123!`.

---

## 5. Running Automated Tests

Run the full pytest suite (32 passed unit & integration tests):

```powershell
cd backend
python -m pytest
```

Test coverage includes:
- Phase 1 Date Calculator, Employee CRUD, Dup Email Rules, Pagination Limits, Concurrency Locking.
- Phase 2 Email Job creation, DB `UNIQUE(employee_id, email_type)` constraint, Idempotent Backfill, LWD / Email sync, Transactional Employee & Job Cancellation.
- Atomic Job Claiming, Simulated Worker Concurrency, Failure Classification, Exponential Backoff, Stuck `PROCESSING` Recovery, Send Now Race Protection, and Sandboxed Jinja2 Template rendering.

---

## 6. Worker Health & Observability Endpoint

Check worker health:

```http
GET /api/health/worker
```

Example response:

```json
{
  "status": "healthy",
  "timestamp": "2026-08-20T11:15:00.000000",
  "email_mode": "console",
  "scheduled_jobs": 12,
  "processing_jobs": 0,
  "failed_jobs": 0,
  "sent_jobs": 5,
  "last_successful_job_at": "2026-08-20T11:14:00.000000"
}
```
