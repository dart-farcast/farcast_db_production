"""
FarCast DB v2 — FastAPI entry point
Run with:  uvicorn app:app --reload --port 5052
"""
import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from api.cache import lifespan
from api.routes import stats, autocomplete, search, upload, auth_routes, admin_routes
from api.auth import get_current_whitelisted_user

app = FastAPI(title='FarCast DB v2', lifespan=lifespan)

# Allow React dev-server to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
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

@app.get('/api/refresh')
async def refresh_cache():
    await run_in_threadpool(reload_cache)
    return {"status": "success", "stats": cache.stats}

# Protected Database Endpoints (Requires valid JWT & Whitelisted Email)
app.include_router(stats.router,        prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(autocomplete.router, prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(search.router,       prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(upload.router,       prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])

@app.get('/api/hardcode')
def hardcode():
    df = cache.assay_dfs.get('Histopathology')
    return {
        'alive': True,
        'unique_sids': int(df['Sample_ID'].nunique()) if df is not None and 'Sample_ID' in df.columns else 0,
        'stats': cache.stats
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
