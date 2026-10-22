"""
FarCast DB — Structured Logger & Metrics Collector for Automated Sync
"""
import os
import sys
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

from config import LOGS_DIR

os.makedirs(LOGS_DIR, exist_ok=True)

@dataclass
class SyncMetrics:
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None
    success: bool = False
    
    # Metadata stats
    meta_total_read: int = 0
    meta_upserted: int = 0
    meta_skipped: int = 0
    
    # Cytokine stats
    cyto_runs_processed: int = 0
    cyto_rows_inserted: int = 0
    cyto_unique_samples: int = 0
    
    # Histopathology stats
    histo_files_processed: int = 0
    histo_rows_inserted: int = 0
    histo_unique_samples: int = 0
    
    # Treatment Overlay stats
    overlay_total_rows: int = 0
    overlay_samples_covered: int = 0
    overlay_unmatched_arms: List[str] = field(default_factory=list)
    
    # Cache Invalidation
    railway_cache_refreshed: bool = False
    local_cache_refreshed: bool = False
    
    # Logs & Alerts
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    critical_error: str = ""

    @property
    def duration_seconds(self) -> float:
        if not self.end_time:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": round(self.duration_seconds, 2),
            "success": self.success,
            "metadata": {
                "total_read": self.meta_total_read,
                "upserted": self.meta_upserted,
                "skipped": self.meta_skipped,
            },
            "cytokine": {
                "runs_processed": self.cyto_runs_processed,
                "rows_inserted": self.cyto_rows_inserted,
                "unique_samples": self.cyto_unique_samples,
            },
            "histopathology": {
                "files_processed": self.histo_files_processed,
                "rows_inserted": self.histo_rows_inserted,
                "unique_samples": self.histo_unique_samples,
            },
            "overlay": {
                "total_rows": self.overlay_total_rows,
                "samples_covered": self.overlay_samples_covered,
                "unmatched_arms": list(set(self.overlay_unmatched_arms)),
            },
            "cache_refreshed": {
                "railway": self.railway_cache_refreshed,
                "local": self.local_cache_refreshed,
            },
            "warnings_count": len(self.warnings),
            "errors_count": len(self.errors),
            "critical_error": self.critical_error,
        }


def setup_sync_logger() -> tuple[logging.Logger, str]:
    """Setup dual logger to stdout and timestamped file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = f"sync_{timestamp}.log"
    log_filepath = os.path.join(LOGS_DIR, log_filename)
    latest_filepath = os.path.join(LOGS_DIR, "sync_latest.log")

    logger = logging.getLogger("FarcastSync")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_filepath, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    try:
        latest_fh = logging.FileHandler(latest_filepath, mode="w", encoding="utf-8")
        latest_fh.setLevel(logging.INFO)
        latest_fh.setFormatter(formatter)
        logger.addHandler(latest_fh)
    except Exception:
        pass

    logger.info(f"Initialized sync log file: {log_filepath}")
    return logger, log_filepath
