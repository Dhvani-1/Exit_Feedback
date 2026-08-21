import os
import sys
import time
import signal
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import SessionLocal
from app.services.worker_service import process_due_jobs, recover_stuck_processing_jobs
from app.services.backfill_service import backfill_missing_email_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WORKER] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("worker_runner")

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Received shutdown signal. Stopping worker gracefully...")
    running = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


def run_worker_loop(poll_interval: int = 10):
    worker_id = f"worker_{os.getpid()}"
    logger.info(f"Starting standalone email background worker '{worker_id}' (poll interval: {poll_interval}s)")

    # Perform initial idempotent backfill
    db = SessionLocal()
    try:
        backfilled = backfill_missing_email_jobs(db)
        if backfilled > 0:
            logger.info(f"Initial backfill created {backfilled} missing email jobs")
    except Exception as e:
        logger.error(f"Backfill error: {e}")
    finally:
        db.close()

    while running:
        db = SessionLocal()
        try:
            # 1. Recover stuck jobs
            recovered = recover_stuck_processing_jobs(db)
            if recovered > 0:
                logger.info(f"Recovered {recovered} stuck processing jobs")

            # 2. Process due jobs
            processed = process_due_jobs(db, worker_id=worker_id)
            if processed > 0:
                logger.info(f"Processed {processed} due email jobs")

        except Exception as e:
            logger.error(f"Error in worker iteration loop: {e}", exc_info=True)
        finally:
            db.close()

        # Sleep in small steps to allow fast shutdown response
        for _ in range(poll_interval):
            if not running:
                break
            time.sleep(1)

    logger.info("Worker stopped cleanly.")


if __name__ == "__main__":
    run_worker_loop()
