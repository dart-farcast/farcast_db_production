"""
FarCast DB v2 — Authentication & Whitelist Core Module
SQLite database management, password hashing, JWT tokens, and security helpers.
"""
import os
import sqlite3
import uuid
import time
from datetime import datetime, timedelta
from typing import Optional, Iterable, Set, Dict, Any
import jwt
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'auth.db')
SECRET_KEY = os.environ.get('JWT_SECRET', 'farcast_db_super_secret_jwt_key_2026_x89a')
ALGORITHM = "HS256"
TOKEN_ISSUER = "farcast-db-v2"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', str(7 * 24 * 60)))  # Default 7 days

security_scheme = HTTPBearer(auto_error=False)

from database.db_client import get_db_connection
from database.auth_db import (
    hash_password, verify_password, is_email_whitelisted,
    init_auth_db, log_audit_event, revoke_token, is_token_revoked,
    validate_password_strength
)

def get_db():
    return get_db_connection()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a secure signed JWT with unique jti, iat, and issuer claims."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    jti = str(uuid.uuid4())
    to_encode.update({
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": TOKEN_ISSUER,
        "jti": jti,
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes, validates claims, and verifies token revocation state against the blacklist."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            options={"require": ["exp", "iat", "sub"]}
        )
        jti = payload.get("jti")
        if jti and is_token_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please sign in again."
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again."
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer."
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )

# Initialize database on import
init_auth_db()

# In-memory user cache for instant token authorization (TTL: 60s)
_USER_CACHE: Dict[str, tuple[float, dict]] = {}

def clear_user_cache(email: Optional[str] = None):
    """Invalidates the user memory cache for a specific email or all users."""
    global _USER_CACHE
    if email:
        _USER_CACHE.pop(email.strip().lower(), None)
    else:
        _USER_CACHE.clear()


# ── Dependencies ─────────────────────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """FastAPI dependency to extract and return current authenticated user with caching."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in."
        )
    token_str = credentials.credentials
    payload = decode_access_token(token_str)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    
    clean_email = email.strip().lower()
    now_ts = time.time()

    # Fast in-memory cache check (TTL: 60 seconds)
    if clean_email in _USER_CACHE:
        cached_ts, cached_user = _USER_CACHE[clean_email]
        if now_ts - cached_ts < 60:
            user_dict = dict(cached_user)
            user_dict['token_jti'] = payload.get("jti")
            user_dict['token_exp'] = payload.get("exp")
            return user_dict
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, role, is_whitelisted, allowed_studies FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User account not found.")
        
        user_dict = dict(user)
        # Parse allowed_studies
        raw_studies = user_dict.get('allowed_studies', '*')
        if raw_studies != '*' and isinstance(raw_studies, str):
            user_dict['allowed_studies'] = [s.strip() for s in raw_studies.split(',') if s.strip()]
        else:
            user_dict['allowed_studies'] = '*'

        # Re-check whitelist dynamically
        if not user_dict['is_whitelisted'] and is_email_whitelisted(user_dict['email']):
            cursor.execute("UPDATE users SET is_whitelisted = TRUE WHERE email = ?", (user_dict['email'],))
            conn.commit()
            user_dict['is_whitelisted'] = True

        # Store in cache
        _USER_CACHE[clean_email] = (now_ts, dict(user_dict))

        # Attach token metadata for session management / logout
        user_dict['token_jti'] = payload.get("jti")
        user_dict['token_exp'] = payload.get("exp")

        return user_dict


def get_current_whitelisted_user(current_user: dict = Depends(get_current_user)):
    """Dependency that ensures user is authenticated AND whitelisted."""
    if not current_user.get("is_whitelisted"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email address has not been whitelisted by an administrator yet."
        )
    return current_user

def get_current_admin_user(current_user: dict = Depends(get_current_whitelisted_user)):
    """Dependency that ensures user is authenticated, whitelisted AND an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required for this operation."
        )
    return current_user


# ── Study-Level Authorization Helper ──────────────────────────────────────────

def verify_user_sample_access(current_user: dict, sample_id: str) -> bool:
    """Verifies whether current user is permitted to view data for given sample ID."""
    allowed = current_user.get('allowed_studies', '*')
    if allowed == '*':
        return True
    if not isinstance(allowed, list):
        return True

    from .cache import cache
    meta_row = cache.meta_idx.get(sample_id.strip())
    if not meta_row:
        # If metadata row is missing from memory, check if sample belongs to study index
        study_idx = cache.indexes.get('study', {})
        for s in allowed:
            if sample_id.strip() in study_idx.get(s.strip().lower(), set()):
                return True
        return False

    sample_study = str(meta_row.get('Study', '')).strip().lower()
    allowed_set = {s.strip().lower() for s in allowed}
    return sample_study in allowed_set

def filter_samples_by_user_scope(current_user: dict, sample_ids: Iterable[str]) -> set:
    """Filters a collection of sample IDs to only those permitted for current user."""
    allowed = current_user.get('allowed_studies', '*')
    if allowed == '*':
        return {s.strip() for s in sample_ids if s and s.strip()}
    if not isinstance(allowed, list):
        return {s.strip() for s in sample_ids if s and s.strip()}

    from .cache import cache
    allowed_set = {s.strip().lower() for s in allowed}
    permitted = set()
    study_idx = cache.indexes.get('study', {})

    allowed_sids_universe = set()
    for s in allowed_set:
        allowed_sids_universe |= study_idx.get(s, set())

    for sid in sample_ids:
        s_clean = sid.strip() if isinstance(sid, str) else ''
        if not s_clean:
            continue
        if s_clean in allowed_sids_universe:
            permitted.add(s_clean)
        else:
            meta_row = cache.meta_idx.get(s_clean)
            if meta_row and str(meta_row.get('Study', '')).strip().lower() in allowed_set:
                permitted.add(s_clean)

    return permitted

