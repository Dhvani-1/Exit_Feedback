from datetime import datetime
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.models.email_job import EmailJob, EmailJobStatus
from app.routes import auth, employees, dashboard, email_jobs, settings as settings_route, feedback, excel, reports
from app.services.backfill_service import backfill_missing_email_jobs
from app.utils.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Custom Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(excel.router, prefix=settings.API_V1_STR)
app.include_router(employees.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(email_jobs.router, prefix=settings.API_V1_STR)
app.include_router(settings_route.router, prefix=settings.API_V1_STR)
app.include_router(feedback.router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def on_startup():
    """Application startup tasks: initialize tables, run idempotent backfill and optional embedded worker thread."""
    import os
    import threading
    from app.database.init_db import init_db
    from app.database.connection import SessionLocal

    # 1. Ensure all database tables exist and initial templates are seeded
    init_db()

    # 2. Perform backfill check
    db = SessionLocal()
    try:
        backfill_missing_email_jobs(db)
    except Exception as e:
        print(f"[!] Startup backfill notice: {e}")
    finally:
        db.close()

    if os.environ.get("ENABLE_EMBEDDED_WORKER", "true").lower() in ("true", "1", "yes"):
        try:
            from run_worker import run_worker_loop
            worker_thread = threading.Thread(target=run_worker_loop, kwargs={"poll_interval": 10}, daemon=True)
            worker_thread.start()
            print("[SUCCESS] Embedded background email worker thread started successfully!")
        except Exception as we:
            print(f"[!] Embedded worker thread error: {we}")


@app.get("/api/health")
def health_check():
    """Application health check endpoint."""
    return {"status": "ok", "environment": settings.ENVIRONMENT, "version": settings.VERSION}


@app.get("/api/health/worker")
def worker_health_check(db: Session = Depends(get_db)):
    """Worker and email jobs health monitoring endpoint."""
    scheduled_count = (
        db.query(func.count(EmailJob.id))
        .filter(EmailJob.status == EmailJobStatus.SCHEDULED)
        .scalar()
        or 0
    )
    processing_count = (
        db.query(func.count(EmailJob.id))
        .filter(EmailJob.status == EmailJobStatus.PROCESSING)
        .scalar()
        or 0
    )
    failed_count = (
        db.query(func.count(EmailJob.id))
        .filter(EmailJob.status == EmailJobStatus.FAILED)
        .scalar()
        or 0
    )
    sent_count = (
        db.query(func.count(EmailJob.id))
        .filter(EmailJob.status == EmailJobStatus.SENT)
        .scalar()
        or 0
    )

    last_job = (
        db.query(EmailJob)
        .filter(EmailJob.status == EmailJobStatus.SENT)
        .order_by(EmailJob.sent_at.desc())
        .first()
    )

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "email_mode": settings.EMAIL_MODE,
        "scheduled_jobs": scheduled_count,
        "processing_jobs": processing_count,
        "failed_jobs": failed_count,
        "sent_jobs": sent_count,
        "last_successful_job_at": last_job.sent_at.isoformat() if last_job and last_job.sent_at else None,
    }
