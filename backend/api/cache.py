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
    # quick lookup: {sample_id: first metadata row as dict}
    meta_idx:       dict         = field(default_factory=dict)
    # reverse lookup: {assay_name: set(sample_ids)}
    assay_sids_map: dict         = field(default_factory=dict)


cache = AppCache()


def reload_cache():
    """Reload all data into the memory cache."""
    print("  FarCast DB v2: reloading data...")
    cache.metadata       = load_metadata()
    cache.overlay        = build_overlay()
    cache.assay_paths    = discover_assays()
    cache.assay_dfs      = load_assay_dfs(cache.assay_paths)
    cache.assay_presence = build_assay_presence_map(cache.assay_dfs)
    cache.stats          = compute_stats(cache.metadata, cache.overlay, cache.assay_dfs)
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

    print(f"  Loaded {cache.stats.get('samples', 0)} samples, "
          f"{len(cache.assay_dfs)} assays - ready.")


from fastapi.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load everything into memory on startup."""
    await run_in_threadpool(reload_cache)
    yield
    # nothing to clean up
