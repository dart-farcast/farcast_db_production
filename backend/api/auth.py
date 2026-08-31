"""
FarCast DB v2 — Authentication & Whitelist Core Module
SQLite database management, password hashing, JWT tokens, and security helpers.
"""
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'auth.db')
SECRET_KEY = os.environ.get('JWT_SECRET', 'farcast_db_super_secret_jwt_key_2026_x89a')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security_scheme = HTTPBearer(auto_error=False)

from database.db_client import get_db_connection
from database.auth_db import (
    hash_password, verify_password, is_email_whitelisted,
    init_auth_db, log_audit_event
)

def get_db():
    return get_db_connection()

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Generates a JWT token valid for specified duration."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please sign in again."
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token."
        )

# Initialize database on import
init_auth_db()


# ── Dependencies ─────────────────────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """FastAPI dependency to extract and return current authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in."
        )
    payload = decode_access_token(credentials.credentials)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    
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
            cursor.execute("UPDATE users SET is_whitelisted = 1 WHERE email = ?", (user_dict['email'],))
            conn.commit()
            user_dict['is_whitelisted'] = 1

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
