"""
FarCast DB — Master Office Server to Supabase Ingestion Orchestrator
Execute manually or schedule via Windows Task Scheduler.
Usage: python sync_all.py
"""
import sys
import os
import json
import time
import traceback
import requests
from datetime import datetime
from sqlalchemy import text, create_engine

# Ensure current directory is on sys.path
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from config import (
    DATABASE_URL, RAILWAY_APP_URL, LOCAL_REFRESH_URL,
    MAX_NETWORK_RETRIES, RETRY_DELAY_SECONDS
)
from logger import setup_sync_logger, SyncMetrics
from email_notifier import send_sync_email
from metadata_sync import sync_metadata
from assay_sync import sync_cytokine_assays, sync_histopathology_assays
from nomenclature_resolver import sync_treatment_overlay


def get_verified_db_engine(logger):
    """Establish and verify database connection with retries."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is not configured in .env")

    db_url = DATABASE_URL
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
    elif db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    for attempt in range(1, MAX_NETWORK_RETRIES + 1):
        try:
            logger.info(f"Connecting to Supabase (Attempt {attempt}/{MAX_NETWORK_RETRIES})...")
            engine = create_engine(db_url, connect_args={'connect_timeout': 15})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Supabase database connection established successfully.")
            return engine
        except Exception as e:
            logger.warning(f"Connection attempt {attempt} failed: {e}")
            if attempt < MAX_NETWORK_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                raise ConnectionError(f"Failed to connect to Supabase after {MAX_NETWORK_RETRIES} attempts: {e}")


def reload_portal_caches(metrics: SyncMetrics, logger):
    """Trigger zero-downtime in-memory cache refresh on Local and Railway instances."""
    logger.info("=" * 60)
    logger.info("STEP 4: Triggering Zero-Downtime Cache Invalidation")
    logger.info("=" * 60)

    # 1. Local Cache Refresh
    if LOCAL_REFRESH_URL:
        try:
            r = requests.get(LOCAL_REFRESH_URL, timeout=60)
            if r.status_code == 200:
                logger.info(f"Local FastAPI cache successfully reloaded: {r.status_code}")
                metrics.local_cache_refreshed = True
            else:
                logger.warning(f"Local cache refresh returned status: {r.status_code}")
        except Exception as e:
            logger.info(f"Local cache reload skipped (local server may not be running): {e}")

    # 2. Railway Production Cache Refresh
    if RAILWAY_APP_URL:
        railway_refresh_endpoint = f"{RAILWAY_APP_URL}/api/refresh"
        try:
            logger.info(f"Pinging Railway production cache: {railway_refresh_endpoint}...")
            r = requests.get(railway_refresh_endpoint, timeout=30)
            if r.status_code == 200:
                logger.info(f"Railway production cache successfully refreshed: {r.status_code}")
                metrics.railway_cache_refreshed = True
            else:
                logger.warning(f"Railway cache refresh returned status: {r.status_code}")
        except Exception as e:
            logger.warning(f"Railway production cache refresh ping failed: {e}")
            metrics.warnings.append(f"Railway cache reload notice: {e}")


def record_audit_log(engine, metrics: SyncMetrics, logger):
    """Record execution details into Supabase audit_logs."""
    try:
        summary_json = json.dumps(metrics.to_dict(), default=str)
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(
                    text("""
                        INSERT INTO "audit_logs" (actor_email, action, details, timestamp)
                        VALUES (:actor, :action, :details, NOW())
                    """),
                    {
                        'actor': 'system_office_cron',
                        'action': 'OFFICE_SERVER_SYNC',
                        'details': f"Status: {'SUCCESS' if metrics.success else 'FAILED'}. Summary: {summary_json}"
                    }
                )
        logger.info("Recorded sync execution log into Supabase 'audit_logs'.")
    except Exception as e:
        logger.warning(f"Failed to record audit log: {e}")


def run_pipeline() -> bool:
    """Main execution function with top-level error catching and email alerting."""
    logger, log_filepath = setup_sync_logger()
    metrics = SyncMetrics()
    engine = None

    logger.info("=" * 75)
    logger.info("  FARCAST BIOSCIENCES — AUTOMATED OFFICE SERVER TO SUPABASE SYNC")
    logger.info("=" * 75)
    logger.info(f"Start Time: {metrics.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        engine = get_verified_db_engine(logger)

        sync_metadata(engine, metrics, logger)
        sync_cytokine_assays(engine, metrics, logger)
        sync_histopathology_assays(engine, metrics, logger)
        sync_treatment_overlay(engine, metrics, logger)
        reload_portal_caches(metrics, logger)

        metrics.success = True
        logger.info("=" * 75)
        logger.info("  SYNC PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
        logger.info("=" * 75)

    except Exception as exc:
        metrics.success = False
        tb = traceback.format_exc()
        metrics.critical_error = f"{exc}\n{tb}"
        logger.critical(f"FATAL PIPELINE CRASH: {exc}")
        logger.critical(tb)

    finally:
        metrics.end_time = datetime.now()
        logger.info(f"Total Execution Time: {metrics.duration_seconds:.2f} seconds.")

        if engine:
            record_audit_log(engine, metrics, logger)

        logger.info("Dispatching email notification...")
        send_sync_email(metrics, log_filepath, logger)

    return metrics.success


if __name__ == '__main__':
    success = run_pipeline()
    sys.exit(0 if success else 1)
