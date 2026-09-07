"""
FarCast DB v2 — FastAPI Production Entry Point
Hardened with OWASP security headers, sliding-window rate limiting,
request correlation tracking, atomic health probes, and structured error envelopes.
"""
import os
import time
import uuid
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, Depends, Request, Response, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.cache import lifespan, cache, reload_cache
from api.routes import stats, autocomplete, search, upload, auth_routes, admin_routes
from api.auth import get_current_whitelisted_user, get_db

app = FastAPI(
    title='FarCast DB v2',
    description='Production Multi-Omics Research Database with Study-Level RBAC',
    version='2.2.0',
    lifespan=lifespan
)


# ── 1. Request ID & Structured Logging Middleware ─────────────────────────────

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.time()
        
        response: Response = await call_next(request)
        
        latency = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{latency}ms"
        return response

app.add_middleware(RequestContextMiddleware)


# ── 2. OWASP Security Headers Middleware ──────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Enforce HSTS for HTTPS connections in production
        if request.url.scheme == "https" or os.environ.get("ENVIRONMENT") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ── 3. Sliding-Window Rate Limiting Middleware ────────────────────────────────

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        # Endpoint path prefix -> (max_requests, window_seconds)
        self.limits = {
            "/api/auth/login":    (15, 60),   # 15 login attempts per min
            "/api/auth/register": (10, 60),   # 10 registrations per min
            "/api/refresh":       (5, 60),    # 5 cache refreshes per min
            "/api/search":        (180, 60),  # 180 search queries per min
            "/api/autocomplete":  (360, 60),  # 360 autocomplete lookups per min
        }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        # Check if route matches rate limit rules
        for prefix, (max_reqs, window) in self.limits.items():
            if path.startswith(prefix):
                key = f"{client_ip}:{prefix}"
                now = time.time()
                # Prune timestamps outside window
                self.requests[key] = [t for t in self.requests[key] if now - t < window]

                if len(self.requests[key]) >= max_reqs:
                    req_id = getattr(request.state, "request_id", "")
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": {
                                "code": "TOO_MANY_REQUESTS",
                                "message": f"Rate limit exceeded. Please wait before making more requests.",
                                "request_id": req_id
                            }
                        },
                        headers={"Retry-After": str(window)}
                    )
                self.requests[key].append(now)
                break

        return await call_next(request)

app.add_middleware(RateLimiterMiddleware)


# ── 4. CORS Configuration ─────────────────────────────────────────────────────

allowed_origins_env = os.environ.get('ALLOWED_ORIGINS', '')
if allowed_origins_env:
    origins = [o.strip() for o in allowed_origins_env.split(',') if o.strip()]
else:
    origins = [
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:5052',
        'http://127.0.0.1:5052',
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['*'],
    expose_headers=['X-Request-ID', 'X-Response-Time'],
)


# ── 5. Standardized Error Handling ────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "request_id": req_id
            }
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "")
    print(f"  [ERROR] Unhandled exception (Request ID {req_id}): {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "request_id": req_id
            }
        }
    )


# ── 6. Health & Readiness Probes ──────────────────────────────────────────────

@app.get('/health/live', tags=['monitoring'])
def liveness_probe():
    """Liveness probe: returns 200 if FastAPI process is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get('/health/ready', tags=['monitoring'])
def readiness_probe():
    """Readiness probe: validates database connectivity and in-memory cache integrity."""
    # 1. Verify Cache Readiness
    if not cache.is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "reason": "In-memory cache is still initializing or encountered an error.",
                "cache_error": cache.last_error
            }
        )

    # 2. Verify Database Connection
    db_ok = True
    db_err = None
    try:
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as e:
        db_ok = False
        db_err = str(e)

    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "reason": "Database connection check failed.",
                "db_error": db_err
            }
        )

    return {
        "status": "ready",
        "cache_version": cache.version,
        "samples_loaded": cache.stats.get("samples", 0),
        "assays_loaded": len(cache.assay_dfs),
        "last_cache_update": cache.last_loaded_at,
        "timestamp": datetime.utcnow().isoformat()
    }


# ── 7. Route Registrations ───────────────────────────────────────────────────

# Public Auth Endpoints
app.include_router(auth_routes.router, prefix='/api')

# Admin Endpoints (Auth dependencies enforced internally)
app.include_router(admin_routes.router, prefix='/api')

from fastapi.concurrency import run_in_threadpool

@app.get('/api/refresh')
async def refresh_cache(current_user: dict = Depends(get_current_whitelisted_user)):
    success = await run_in_threadpool(reload_cache)
    return {
        "status": "success" if success else "failed",
        "cache_ready": cache.is_ready,
        "version": cache.version,
        "stats": cache.stats
    }

# Protected Database Endpoints (Requires valid JWT & Whitelisted Email)
app.include_router(stats.router,        prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(autocomplete.router, prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(search.router,       prefix='/api', dependencies=[Depends(get_current_whitelisted_user)])
app.include_router(upload.router,       prefix='/api')

@app.get('/api/hardcode')
def hardcode():
    df = cache.assay_dfs.get('Histopathology')
    return {
        'alive': True,
        'ready': cache.is_ready,
        'unique_sids': int(df['Sample_ID'].nunique()) if df is not None and 'Sample_ID' in df.columns else 0,
        'stats': cache.stats
    }


# ── 8. Serve React Production Build with Aggressive Asset Caching ────────────

FRONTEND_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))

class CachedStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs) -> Response:
        resp = super().file_response(*args, **kwargs)
        # Hashed assets in /assets are immutable and cached for 1 year
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp

if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, 'assets')
    if os.path.isdir(assets_dir):
        app.mount('/assets', CachedStaticFiles(directory=assets_dir), name='assets')

    @app.get('/{full_path:path}', include_in_schema=False)
    def spa_fallback(full_path: str):
        target = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if os.path.isfile(target):
            res = FileResponse(target)
            if any(full_path.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.svg', '.ico', '.woff', '.woff2', '.webmanifest')):
                res.headers["Cache-Control"] = "public, max-age=86400"
            return res
        
        # index.html should not be aggressively cached to allow instant updates on deployment
        res = FileResponse(os.path.join(FRONTEND_DIST, 'index.html'))
        res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        res.headers["Pragma"] = "no-cache"
        res.headers["Expires"] = "0"
        return res
else:
    @app.get('/')
    def root():
        return {'message': 'FarCast DB v2 API. Build the React frontend first.'}


if __name__ == '__main__':
    import uvicorn
    print('\n  FarCast DB v2  ->  http://localhost:5052\n')
    uvicorn.run('app:app', host='0.0.0.0', port=5052, reload=True)

