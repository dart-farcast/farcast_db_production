"""
FarCast DB v2 — FastAPI entry point
Run with:  uvicorn app:app --reload --port 5052

Performance upgrades (2026-11-23):
  - GZip middleware: 60-80% payload reduction on all JSON responses
  - Non-blocking /api/refresh: schedules reload in background, returns immediately
  - Cache reload status endpoint: /api/cache_status
"""
import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.cache import lifespan
from api.routes import stats, autocomplete, search, upload, auth_routes, admin_routes, pre_reboot_routes
from api.auth import get_current_whitelisted_user

app = FastAPI(title='FarCast DB v2', lifespan=lifespan)

# ── GZip compression: compress any response >= 1 KB (JSON, HTML, text) ───────
# This slashes bandwidth ~60-80% on large search result payloads.
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── CORS: allow React dev-server and production Railway domain ────────────────
RAILWAY_URL = os.environ.get('RAILWAY_APP_URL', '').rstrip('/')
_cors_origins = ['http://localhost:5173', 'http://127.0.0.1:5173']
if RAILWAY_URL:
    _cors_origins.append(RAILWAY_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Unprotected Public Auth Endpoints
app.include_router(auth_routes.router, prefix='/api')

# Admin Console Endpoints (Internal auth checks within admin_routes)
app.include_router(admin_routes.router, prefix='/api')

from fastapi.concurrency import run_in_threadpool
from api.cache import cache, reload_cache
import time

# ── Non-blocking cache refresh ────────────────────────────────────────────────
# Old behaviour: awaited reload_cache() — blocked ALL requests for 30-60s.
# New behaviour: schedules reload as a BackgroundTask, returns immediately.
#   - Stale (previous good) data continues serving while reload runs.
#   - Use GET /api/cache_status to poll completion.

def _bg_reload():
    """Background thread target — wraps reload_cache for BackgroundTasks."""
    reload_cache()

@app.api_route('/api/refresh', methods=['GET', 'POST'])
async def refresh_cache(background_tasks: BackgroundTasks):
    """
    Schedule a non-blocking cache reload.
    Returns immediately with current cache snapshot.
    Poll /api/cache_status to know when the reload finishes.
    """
    if cache.is_reloading:
        return {
            "status": "already_reloading",
            "message": "A reload is already in progress — check /api/cache_status",
            "meta_len": len(cache.metadata),
            "overlay_len": len(cache.overlay),
            "assays": {k: len(v) for k, v in cache.assay_dfs.items()},
        }

    background_tasks.add_task(_bg_reload)
    return {
        "status": "reload_scheduled",
        "message": "Cache reload started in background. Data continues serving. Poll /api/cache_status.",
        "meta_len": len(cache.metadata),
        "overlay_len": len(cache.overlay),
        "assays": {k: len(v) for k, v in cache.assay_dfs.items()},
    }


@app.get('/api/cache_status')
async def cache_status():
    """Return current cache state — use to poll after /api/refresh."""
    age_seconds = int(time.time() - cache.last_loaded_at) if cache.last_loaded_at else None
    return {
        "is_reloading":    cache.is_reloading,
        "last_error":      cache.last_error or None,
        "age_seconds":     age_seconds,
        "meta_len":        len(cache.metadata),
        "overlay_len":     len(cache.overlay),
        "pre_reboot_len":  len(cache.pre_reboot_metadata),
        "assays":          {k: len(v) for k, v in cache.assay_dfs.items()},
        "stats_samples":   cache.stats.get('samples', 0),
    }

@app.get('/api/test_db')
def test_db():
    import traceback
    from database.data_loader import get_db_engine
    from sqlalchemy import text
    import os

    raw_url = os.environ.get('DATABASE_URL', '')
    masked_url = raw_url.split('@')[-1] if '@' in raw_url else (raw_url[:15] + '...') if raw_url else 'EMPTY'

    result = {
        'has_env_DATABASE_URL': bool(raw_url),
        'db_host_info': masked_url,
        'metadata_cnt': None,
        'overlay_cnt': None,
        'histo_cnt': None,
        'flow_cnt': None,
        'error': None
    }
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            result['metadata_cnt'] = conn.execute(text('SELECT count(*) FROM "metadata"')).scalar()
            result['overlay_cnt'] = conn.execute(text('SELECT count(*) FROM "overlay"')).scalar()
            result['histo_cnt'] = conn.execute(text('SELECT count(*) FROM "assay_histopathology"')).scalar()
            result['flow_cnt'] = conn.execute(text('SELECT count(*) FROM "assay_flow_cytometry"')).scalar()
    except Exception as e:
        result['error'] = f"{e}\n{traceback.format_exc()}"

    return result

# Protected Database Endpoints (Requires valid JWT & Whitelisted Email)
app.include_router(stats.router,        prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(autocomplete.router, prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(search.router,       prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(upload.router,       prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(pre_reboot_routes.router, prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])

@app.get('/api/hardcode')
def hardcode():
    df = cache.assay_dfs.get('Histopathology')
    return {
        'alive': True,
        'unique_sids': int(df['Sample_ID'].nunique()) if df is not None and 'Sample_ID' in df.columns else 0,
        'last_error': cache.last_error,
        'stats': cache.stats,
        'meta_len': len(cache.metadata),
        'overlay_len': len(cache.overlay),
        'assays': {k: len(v) for k, v in cache.assay_dfs.items()}
    }

# ── Serve React production build ─────────────────────────────────────────────
FRONTEND_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))

if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, 'assets')
    if os.path.isdir(assets_dir):
        app.mount('/assets', StaticFiles(directory=assets_dir), name='assets')

    @app.get('/{full_path:path}', include_in_schema=False)
    def spa_fallback(full_path: str):
        target = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))
else:
    @app.get('/')
    def root():
        return {'message': 'FarCast DB v2 API. Build the React frontend first.'}


if __name__ == '__main__':
    import uvicorn
    print('\n  FarCast DB v2  ->  http://localhost:5052\n')
    uvicorn.run('app:app', host='0.0.0.0', port=5052, reload=True)
