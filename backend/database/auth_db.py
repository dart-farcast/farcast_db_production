"""
FarCast DB v2 — Database User & Auth Access Layer
Isolated queries for User Management, Whitelist Control, RBAC Study Access, and Audit Logging.
"""
import secrets
import hashlib
from typing import Optional, List, Dict, Any
from .db_client import get_db_connection

def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 with HMAC-SHA256 and a random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
    ).hex()
    return f"{salt}${pw_hash}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verifies plain password against stored salt$hash format."""
    try:
        salt, expected_hash = stored_hash.split('$', 1)
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        ).hex()
        return secrets.compare_digest(pw_hash, expected_hash)
    except Exception:
        return False

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates password against security baseline:
    - Minimum 8 characters, maximum 128 characters
    - Must contain at least one uppercase letter, one lowercase letter, and one digit
    - Rejects common trivial passwords
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numeric digit."
    
    common_weak = {"password", "password123", "admin1234", "qwerty123", "letmein123", "farcast123"}
    if password.lower() in common_weak:
        return False, "Password is too common or easily guessable. Please choose a stronger password."

    return True, ""

def is_email_whitelisted(email: str) -> bool:
    """Checks if an email matches a whitelisted email or domain pattern."""
    email_clean = email.strip().lower()
    domain = '@' + email_clean.split('@')[-1] if '@' in email_clean else ''
    
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("SELECT pattern FROM whitelisted_emails")
        rows = cursor.fetchall()
        for row in rows:
            pat = row['pattern'].strip().lower()
            if pat == email_clean or (pat.startswith('@') and pat == domain):
                return True
    return False

def init_auth_db():
    """Initializes tables and seeds initial admin and domain rules if empty."""
    with get_db_connection() as db:
        cursor = db.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_whitelisted INTEGER NOT NULL DEFAULT 0,
                allowed_studies TEXT NOT NULL DEFAULT '*',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Whitelisted emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelisted_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE NOT NULL,
                added_by TEXT DEFAULT 'System',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_email TEXT,
                action TEXT NOT NULL,
                details TEXT,
                request_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Token blacklist table (Revoked JWTs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jti TEXT UNIQUE NOT NULL,
                revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        db.commit()

        # Populate in-memory blacklist cache on init
        cursor.execute("SELECT jti FROM token_blacklist")
        for r in cursor.fetchall():
            if r.get('jti'):
                _REVOKED_JTIS.add(r['jti'])

        # Seed default whitelist rules if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM whitelisted_emails")
        row = cursor.fetchone()
        if not row or row['cnt'] == 0:
            cursor.execute("INSERT INTO whitelisted_emails (pattern, notes) VALUES (?, ?)", 
                           ("admin@farcastbio.com", "Default Admin Email"))
            cursor.execute("INSERT INTO whitelisted_emails (pattern, notes) VALUES (?, ?)", 
                           ("@farcastbio.com", "FarCast Bio Company Domain"))
            db.commit()

        # Seed default admin user if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        row_user = cursor.fetchone()
        if not row_user or row_user['cnt'] == 0:
            hashed_pw = hash_password("admin123")
            cursor.execute("""
                INSERT INTO users (email, full_name, password_hash, role, is_whitelisted, allowed_studies)
                VALUES (?, ?, ?, ?, TRUE, '*')
            """, ("admin@farcastbio.com", "Default Admin", hashed_pw, "admin"))
            db.commit()
            print("  [Auth DB] Initialized auth database with default admin: admin@farcastbio.com / admin123")


_REVOKED_JTIS: set[str] = set()

def revoke_token(jti: str, expires_at: Optional[str] = None):
    """Adds a JWT token identifier (jti) to the revocation blacklist and memory set."""
    if not jti:
        return
    _REVOKED_JTIS.add(jti)
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO token_blacklist (jti, expires_at) VALUES (?, ?)", (jti, expires_at))
            db.commit()
    except Exception:
        pass

def is_token_revoked(jti: str) -> bool:
    """Checks if a JWT jti exists in the revocation blacklist (0ms memory check)."""
    if not jti:
        return False
    return jti in _REVOKED_JTIS

def log_audit_event(actor_email: str, action: str, details: str, request_id: Optional[str] = None):
    """Records security audit log entry with optional request correlation ID."""
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO audit_logs (actor_email, action, details, request_id) VALUES (?, ?, ?, ?)",
                           (actor_email, action, details, request_id or ""))
            db.commit()
    except Exception:
        pass

