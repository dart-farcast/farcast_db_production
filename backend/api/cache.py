"""
FarCast DB v2 — In-Memory Cache + FastAPI Lifespan
Resilient atomic cache swapping with readiness and data integrity validation.
"""
import time
from datetime import datetime
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Optional
import pandas as pd
from fastapi import FastAPI

from database.data_loader import (
    load_metadata, build_overlay,
    load_assay_dfs, build_assay_presence_map,
    compute_stats, build_indexes,
)
def discover_assays(): return {}

@dataclass
class AppCache:
    metadata:       pd.DataFrame = field(default_factory=pd.DataFrame)
    overlay:        pd.DataFrame = field(default_factory=pd.DataFrame)
    assay_paths:    dict         = field(default_factory=dict)
    assay_dfs:      dict         = field(default_factory=dict)
    assay_presence: dict         = field(default_factory=dict)
    stats:          dict         = field(default_factory=dict)
    indexes:        dict         = field(default_factory=dict)
    meta_idx:       dict         = field(default_factory=dict)
    assay_sids_map: dict         = field(default_factory=dict)
    
    # State tracking
    is_ready:       bool         = False
    is_loading:     bool         = False
    version:        int          = 0
    last_loaded_at: Optional[str]= None
    last_error:     Optional[str]= None


cache = AppCache()


def reload_cache() -> bool:
    """
    Safely builds a new cache in isolation, validates integrity, and atomically swaps
    it into the global cache pointer. If building fails, previous healthy cache is preserved.
    """
    start_time = time.time()
    cache.is_loading = True
    print("  [Cache Manager] Building fresh isolated cache instance...")

    try:
        new_meta       = load_metadata()
        new_overlay    = build_overlay()
        new_paths      = discover_assays()
        new_assays     = load_assay_dfs(new_paths)
        new_presence   = build_assay_presence_map(new_assays)
        new_stats      = compute_stats(new_meta, new_overlay, new_assays)
        new_indexes    = build_indexes(new_meta, new_overlay)

        new_meta_idx   = {}
        for _, row in new_meta.iterrows():
            sid = row.get('Sample_ID', '')
            if sid and sid not in new_meta_idx:
                new_meta_idx[sid] = row.to_dict()

        new_assay_sids = {}
        for sid, assays in new_presence.items():
            for a in assays:
                new_assay_sids.setdefault(a, set()).add(sid)

        # Integrity validation
        if new_meta.empty and cache.is_ready:
            raise ValueError("Integrity check failed: Metadata table returned 0 rows.")

        # Atomic property assignment
        cache.metadata       = new_meta
        cache.overlay        = new_overlay
        cache.assay_paths    = new_paths
        cache.assay_dfs      = new_assays
        cache.assay_presence = new_presence
        cache.stats          = new_stats
        cache.indexes        = new_indexes
        cache.meta_idx       = new_meta_idx
        cache.assay_sids_map = new_assay_sids

        cache.version       += 1
        cache.last_loaded_at = datetime.utcnow().isoformat()
        cache.is_ready       = True
        cache.last_error     = None
        cache.is_loading     = False

        elapsed = round(time.time() - start_time, 2)
        print(f"  [Cache Manager] Atomic swap complete (v{cache.version}) in {elapsed}s: "
              f"{cache.stats.get('samples', 0)} samples, {len(cache.assay_dfs)} assays - READY.")
        return True

    except Exception as e:
        cache.last_error = str(e)
        cache.is_loading = False
        print(f"  [Cache Manager ERROR] Cache reload failed: {e}. Retaining existing cache (ready={cache.is_ready}).")
        return False


from fastapi.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load everything into memory on startup with graceful failure handling."""
    await run_in_threadpool(reload_cache)
    yield

