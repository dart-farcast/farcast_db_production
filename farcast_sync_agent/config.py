"""
FarCast DB — Office Server Synchronization Configuration
"""
import os
from dotenv import load_dotenv

# Load local .env from current agent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ── Office Server Network Paths (UNC) ─────────────────────────────────────────
DEFAULT_METADATA_PATH = r"\\in-fs1\Farcast R&D\Farcast 2.0\Sample tracking\FARCAST REBOOT\Sample Registration sheet\Post ReBoot all sample data_2020 to till.xlsx"
DEFAULT_NOMENCLATURE_PATH = r"\\in-fs1\Farcast R&D\Farcast 2.0\Explant Culture\Arm details & Nomenclature for R&D\Nomenclature_protected_Mar2025.xlsx"
DEFAULT_HISTOPATHOLOGY_DIR = r"\\in-fs1\Farcast R&D\Farcast 2.0\Data ingestion\File_output_repo\Assays\Histopathology"
DEFAULT_CYTOKINE_DIR = r"\\in-fs1\Farcast R&D\Farcast 2.0\Data ingestion\File_output_repo\Assays\Cytokine"

DEFAULT_HISTO_ARCHIVE_DIR = r"\\in-fs1\Farcast R&D\Farcast 2.0\Data ingestion\Processing_repo\Archive\Histopathology"
DEFAULT_HISTO_PROCESSING_DIR = r"\\in-fs1\Farcast R&D\Farcast 2.0\Data ingestion\Processing_repo\Assays\Histopathology"

METADATA_EXCEL_PATH = os.environ.get("SYNC_METADATA_PATH", DEFAULT_METADATA_PATH).strip()
NOMENCLATURE_EXCEL_PATH = os.environ.get("SYNC_NOMENCLATURE_PATH", DEFAULT_NOMENCLATURE_PATH).strip()
HISTOPATHOLOGY_DIR = os.environ.get("SYNC_HISTOPATHOLOGY_DIR", DEFAULT_HISTOPATHOLOGY_DIR).strip()
CYTOKINE_DIR = os.environ.get("SYNC_CYTOKINE_DIR", DEFAULT_CYTOKINE_DIR).strip()

HISTO_ARCHIVE_DIR = os.environ.get("SYNC_HISTO_ARCHIVE_DIR", DEFAULT_HISTO_ARCHIVE_DIR).strip()
HISTO_PROCESSING_DIR = os.environ.get("SYNC_HISTO_PROCESSING_DIR", DEFAULT_HISTO_PROCESSING_DIR).strip()

# ── Database & Cache Reload Settings ──────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
RAILWAY_APP_URL = os.environ.get("RAILWAY_APP_URL", "").strip().rstrip("/")
LOCAL_REFRESH_URL = os.environ.get("LOCAL_REFRESH_URL", "http://localhost:5052/api/refresh").strip()

# ── Email Alerting & Digest Settings ──────────────────────────────────────────
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "").strip() or SMTP_USER
NOTIFICATION_EMAILS = [
    e.strip() for e in os.environ.get("NOTIFICATION_EMAILS", "somanath@farcastbio.com").split(",") if e.strip()
]

# ── Operational Guardrails ───────────────────────────────────────────────────
CHUNK_SIZE = 500
MAX_NETWORK_RETRIES = 3
RETRY_DELAY_SECONDS = 5
TEMP_CACHE_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), 'temp'))
LOGS_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), 'logs'))
