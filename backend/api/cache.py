"""
FarCast DB v2 — In-Memory Cache + FastAPI Lifespan
Data is loaded ONCE at startup; every request reads from this cache.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
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


cache = AppCache()


def reload_cache():
    """Reload all data into the memory cache."""
    print("  FarCast DB v2: reloading data...")
    cache.last_error = ""
    try:
        # 1. Post-Reboot Multimodal Data
        cache.metadata       = load_metadata()
        cache.overlay        = build_overlay()
        cache.assay_paths    = discover_assays()
        cache.assay_dfs      = load_assay_dfs(cache.assay_paths)
        cache.assay_presence = build_assay_presence_map(cache.assay_dfs)
        cache.stats          = compute_stats(cache.metadata, cache.overlay, cache.assay_dfs, is_scoped=False)
        cache.indexes        = build_indexes(cache.metadata, cache.overlay)

        cache.meta_idx.clear()
        for _, row in cache.metadata.iterrows():
            sid = row.get('Sample_ID', '')
            if sid and sid not in cache.meta_idx:
                cache.meta_idx[sid] = row.to_dict()

        cache.assay_sids_map.clear()
        for sid, assays in cache.assay_presence.items():
            for a in assays:
                cache.assay_sids_map.setdefault(a, set()).add(sid)

        # 2. Pre-Reboot Historical Bio-Repository Data (2017–2020 MBT)
        cache.pre_reboot_metadata = load_pre_reboot_metadata()
        cache.pre_reboot_stats    = compute_pre_reboot_stats(cache.pre_reboot_metadata)
        cache.pre_reboot_indexes  = build_pre_reboot_indexes(cache.pre_reboot_metadata)
        
        cache.pre_reboot_mbt_map.clear()
        if not cache.pre_reboot_metadata.empty:
            for _, row in cache.pre_reboot_metadata.iterrows():
                mbt_val = str(row.get('mbt', '')).strip().upper()
                if mbt_val and mbt_val not in cache.pre_reboot_mbt_map:
                    cache.pre_reboot_mbt_map[mbt_val] = row.to_dict()

        print(f"  Loaded {cache.stats.get('samples', 0)} post-reboot samples, "
              f"{len(cache.pre_reboot_metadata)} pre-reboot historical samples, "
              f"{len(cache.assay_dfs)} assays - ready.")
    except Exception as e:
        import traceback
        cache.last_error = f"{e}\n{traceback.format_exc()}"
        print(f"  [Cache Reload Warning] Error during cache initialization: {e}")


from fastapi.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load everything into memory on startup."""
    await run_in_threadpool(reload_cache)
    yield
    # nothing to clean up
