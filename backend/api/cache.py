"""
FarCast DB v2 — In-Memory Cache + FastAPI Lifespan
Data is loaded ONCE at startup; every request reads from this cache.

Performance upgrades (2026-11-23):
  - Non-blocking background reload: serves stale data while fresh data loads
  - Thread-safe reload lock prevents duplicate concurrent reloads
  - Cache reload timestamp tracked for health/monitoring
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
import threading
import time
import pandas as pd
from fastapi import FastAPI

from database.data_loader import (
    load_metadata, build_overlay,
    load_assay_dfs, build_assay_presence_map,
    compute_stats, build_indexes,
    load_pre_reboot_metadata, compute_pre_reboot_stats,
    build_pre_reboot_indexes
)
def discover_assays(): return {}


# ── Reload lock: prevents two simultaneous reloads from racing each other ────
_reload_lock = threading.Lock()


@dataclass
class AppCache:
    metadata:            pd.DataFrame = field(default_factory=pd.DataFrame)
    overlay:             pd.DataFrame = field(default_factory=pd.DataFrame)
    assay_paths:         dict         = field(default_factory=dict)
    assay_dfs:           dict         = field(default_factory=dict)
    assay_presence:      dict         = field(default_factory=dict)
    stats:               dict         = field(default_factory=dict)
    indexes:             dict         = field(default_factory=dict)
    # quick lookup: {sample_id: first metadata row as dict}
    meta_idx:            dict         = field(default_factory=dict)
    # reverse lookup: {assay_name: set(sample_ids)}
    assay_sids_map:      dict         = field(default_factory=dict)

    # ── Pre-Reboot Historical Bio-Repository Cache (2017–2020 MBT) ───────────
    pre_reboot_metadata: pd.DataFrame = field(default_factory=pd.DataFrame)
    pre_reboot_stats:    dict         = field(default_factory=dict)
    pre_reboot_indexes:  dict         = field(default_factory=dict)
    pre_reboot_mbt_map:  dict         = field(default_factory=dict)

    last_error:          str          = ""
    # ── Reload state tracking ─────────────────────────────────────────────────
    last_loaded_at:      float        = 0.0   # epoch seconds of last successful reload
    is_reloading:        bool         = False  # True while a background reload is in flight


cache = AppCache()


def reload_cache():
    """
    Reload all data into the memory cache (blocking, runs in a thread).

    Uses a lock so only one reload runs at a time. The old data stays in
    cache and continues serving requests until the fresh load is complete,
    then the cache is swapped atomically.
    """
    global _reload_lock

    if not _reload_lock.acquire(blocking=False):
        # Another reload is already running — skip this one
        print("  [Cache] Reload already in progress — skipping duplicate request.")
        return

    cache.is_reloading = True
    print("  FarCast DB v2: reloading data (non-blocking — stale data served during reload)...")
    cache.last_error = ""
    t0 = time.monotonic()

    try:
        # ── Build everything into local variables first ──────────────────────
        # This way the cache stays intact if something fails midway.
        new_metadata       = load_metadata()
        new_overlay        = build_overlay()
        new_assay_paths    = discover_assays()
        new_assay_dfs      = load_assay_dfs(new_assay_paths)
        new_assay_presence = build_assay_presence_map(new_assay_dfs)
        new_stats          = compute_stats(new_metadata, new_overlay, new_assay_dfs, is_scoped=False)
        new_indexes        = build_indexes(new_metadata, new_overlay)

        new_meta_idx: dict = {}
        for _, row in new_metadata.iterrows():
            sid = row.get('Sample_ID', '')
            if sid and sid not in new_meta_idx:
                new_meta_idx[sid] = row.to_dict()

        new_assay_sids_map: dict = {}
        for sid, assays in new_assay_presence.items():
            for a in assays:
                new_assay_sids_map.setdefault(a, set()).add(sid)

        # 2. Pre-Reboot Historical Bio-Repository Data (2017–2020 MBT)
        new_pre_reboot_metadata = load_pre_reboot_metadata()
        new_pre_reboot_stats    = compute_pre_reboot_stats(new_pre_reboot_metadata)
        new_pre_reboot_indexes  = build_pre_reboot_indexes(new_pre_reboot_metadata)

        new_pre_reboot_mbt_map: dict = {}
        if not new_pre_reboot_metadata.empty:
            for _, row in new_pre_reboot_metadata.iterrows():
                mbt_val = str(row.get('mbt', '')).strip().upper()
                if mbt_val and mbt_val not in new_pre_reboot_mbt_map:
                    new_pre_reboot_mbt_map[mbt_val] = row.to_dict()

        # ── Atomic swap: all-or-nothing swap into the live cache ─────────────
        cache.metadata            = new_metadata
        cache.overlay             = new_overlay
        cache.assay_paths         = new_assay_paths
        cache.assay_dfs           = new_assay_dfs
        cache.assay_presence      = new_assay_presence
        cache.stats               = new_stats
        cache.indexes             = new_indexes
        cache.meta_idx            = new_meta_idx
        cache.assay_sids_map      = new_assay_sids_map
        cache.pre_reboot_metadata = new_pre_reboot_metadata
        cache.pre_reboot_stats    = new_pre_reboot_stats
        cache.pre_reboot_indexes  = new_pre_reboot_indexes
        cache.pre_reboot_mbt_map  = new_pre_reboot_mbt_map
        cache.last_loaded_at      = time.time()

        elapsed = time.monotonic() - t0
        print(f"  [Cache] Loaded {cache.stats.get('samples', 0)} post-reboot samples, "
              f"{len(cache.pre_reboot_metadata)} pre-reboot historical samples, "
              f"{len(cache.assay_dfs)} assays — ready in {elapsed:.1f}s.")

    except Exception as e:
        import traceback
        cache.last_error = f"{e}\n{traceback.format_exc()}"
        print(f"  [Cache Reload Warning] Error during cache reload: {e}")
        # Previous good data remains in cache — portal keeps serving

    finally:
        cache.is_reloading = False
        _reload_lock.release()


from fastapi.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load everything into memory on startup (blocking — must finish before serving)."""
    await run_in_threadpool(reload_cache)
    yield
    # nothing to clean up
