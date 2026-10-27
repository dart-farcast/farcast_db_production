"""
FarCast DB v2 — Database User & Auth Access Layer
Isolated queries for User Management, Whitelist Control, RBAC Study Access, Audit Logging,
Password Recovery, Email Verification, Login History, and Security Notifications.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
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
    """Initializes tables, creates column migrations, and seeds initial admin and domain rules if empty."""
    with get_db_connection() as db:
        cursor = db.cursor()
        is_pg = getattr(db, 'is_postgres', False)

        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_whitelisted INTEGER NOT NULL DEFAULT 0,
                allowed_studies TEXT NOT NULL DEFAULT '*',
                allowed_samples TEXT NOT NULL DEFAULT '*',
                can_download INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_verified INTEGER NOT NULL DEFAULT 0,
                deactivated_at TIMESTAMP,
                deactivation_reason TEXT,
                failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                last_password_change TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)
        
        # Column migrations for existing tables
        try:
            if is_pg:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS allowed_samples TEXT NOT NULL DEFAULT '*'")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS can_download INTEGER NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMP WITH TIME ZONE")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS deactivation_reason TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP WITH TIME ZONE")
            else:
                cursor.execute("PRAGMA table_info(users)")
                cols = [col['name'] for col in cursor.fetchall()]
                if 'allowed_samples' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN allowed_samples TEXT NOT NULL DEFAULT '*'")
                if 'can_download' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN can_download INTEGER NOT NULL DEFAULT 0")
                if 'is_active' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
                if 'is_verified' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
                if 'deactivated_at' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN deactivated_at TIMESTAMP")
                if 'deactivation_reason' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN deactivation_reason TEXT")
                if 'failed_login_attempts' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER NOT NULL DEFAULT 0")
                if 'last_password_change' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN last_password_change TIMESTAMP")
            db.commit()
        except Exception:
            db.rollback()

        # 2. Whitelisted emails table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelisted_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern TEXT UNIQUE NOT NULL,
                added_by TEXT DEFAULT 'System',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)

        # 3. Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_email TEXT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Password Resets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                token TEXT NOT NULL,
                code TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Email Verifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                code TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Login History table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT NOT NULL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. Security Notifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                notification_type TEXT NOT NULL DEFAULT 'security',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()

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
                INSERT INTO users (email, full_name, password_hash, role, is_whitelisted, is_active, is_verified, allowed_studies, allowed_samples)
                VALUES (?, ?, ?, ?, TRUE, TRUE, TRUE, '*', '*')
            """, ("admin@farcastbio.com", "Default Admin", hashed_pw, "admin"))
            db.commit()
            print("  [Auth DB] Initialized auth database with default admin: admin@farcastbio.com / admin123")
        else:
            # Ensure admin is always active, whitelisted, and verified
            cursor.execute("""
                UPDATE users SET is_whitelisted = TRUE, is_active = TRUE, is_verified = TRUE 
                WHERE email = 'admin@farcastbio.com'
            """)
            db.commit()


# ── Audit & Security Notifications ───────────────────────────────────────────

def log_audit_event(actor_email: str, action: str, details: str):
    """Records security audit log entry."""
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO audit_logs (actor_email, action, details) VALUES (?, ?, ?)",
                           (actor_email, action, details))
            db.commit()
    except Exception:
        pass

def create_security_notification(email: str, title: str, message: str, notification_type: str = "security"):
    """Creates a real-time security notification for a user."""
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO security_notifications (email, title, message, notification_type, is_read)
                VALUES (?, ?, ?, ?, 0)
            """, (email.strip().lower(), title, message, notification_type))
            db.commit()
    except Exception:
        pass

def get_user_notifications(email: str, limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves recent security notifications for a user."""
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, email, title, message, notification_type, is_read, created_at
            FROM security_notifications
            WHERE LOWER(email) = ?
            ORDER BY id DESC
            LIMIT ?
        """, (email.strip().lower(), limit))
        return cursor.fetchall()

def mark_notification_as_read(notification_id: int, email: str) -> bool:
    """Marks a notification as read."""
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE security_notifications 
            SET is_read = 1 
            WHERE id = ? AND LOWER(email) = ?
        """, (notification_id, email.strip().lower()))
        db.commit()
        return cursor.rowcount > 0

def mark_all_notifications_as_read(email: str) -> int:
    """Marks all notifications as read for a user."""
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE security_notifications 
            SET is_read = 1 
            WHERE LOWER(email) = ? AND is_read = 0
        """, (email.strip().lower(),))
        db.commit()
        return cursor.rowcount


# ── Login History ────────────────────────────────────────────────────────────

def record_login_event(email: str, status: str, ip_address: str = "unknown", 
                       user_agent: str = "unknown", reason: str = ""):
    """Records a login attempt (SUCCESS, FAILED, or BLOCKED) in login_history."""
    try:
        with get_db_connection() as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO login_history (email, ip_address, user_agent, status, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (email.strip().lower(), ip_address or "unknown", user_agent or "unknown", status, reason or ""))
            db.commit()
    except Exception:
        pass

def get_user_login_history(email: str, limit: int = 25) -> List[Dict[str, Any]]:
    """Retrieves login history records for a specific user."""
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, email, ip_address, user_agent, status, reason, timestamp
            FROM login_history
            WHERE LOWER(email) = ?
            ORDER BY id DESC
            LIMIT ?
        """, (email.strip().lower(), limit))
        return cursor.fetchall()

def get_all_login_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves global login activity for administrator review."""
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, email, ip_address, user_agent, status, reason, timestamp
            FROM login_history
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()


# ── Password Recovery ────────────────────────────────────────────────────────

def create_password_reset_token(email: str) -> Dict[str, str]:
    """Generates a secure password reset token and 6-digit pin valid for 1 hour."""
    token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    with get_db_connection() as db:
        cursor = db.cursor()
        # Invalidate old unused tokens
        cursor.execute("UPDATE password_resets SET used = 1 WHERE LOWER(email) = ? AND used = 0", (email.strip().lower(),))
        cursor.execute("""
            INSERT INTO password_resets (email, token, code, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
        """, (email.strip().lower(), token, code, expires_at.isoformat()))
        db.commit()
    return {"token": token, "code": code}

def verify_and_consume_reset_token(email: str, token_or_code: str, new_password_hash: str) -> bool:
    """Verifies reset token/code, updates user password, and marks token as consumed."""
    now_iso = datetime.utcnow().isoformat()
    clean_email = email.strip().lower()
    clean_token = token_or_code.strip()

    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, expires_at FROM password_resets
            WHERE LOWER(email) = ? AND (token = ? OR code = ?) AND used = 0
            ORDER BY id DESC LIMIT 1
        """, (clean_email, clean_token, clean_token))
        reset_entry = cursor.fetchone()
        if not reset_entry:
            return False

        # Check expiration
        expires_at_val = reset_entry['expires_at']
        if isinstance(expires_at_val, str):
            try:
                exp_dt = datetime.fromisoformat(expires_at_val.replace('Z', '+00:00').split('+')[0])
                if datetime.utcnow() > exp_dt:
                    return False
            except Exception:
                pass

        # Mark token used
        cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_entry['id'],))
        
        # Update user password & reset failed attempts
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, failed_login_attempts = 0, last_password_change = ?
            WHERE LOWER(email) = ?
        """, (new_password_hash, now_iso, clean_email))
        db.commit()
        return True


# ── Email Verification ───────────────────────────────────────────────────────

def create_email_verification_token(email: str) -> Dict[str, str]:
    """Generates an email verification 6-digit code and token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = datetime.utcnow() + timedelta(hours=24)

    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO email_verifications (email, code, token, expires_at)
            VALUES (?, ?, ?, ?)
        """, (email.strip().lower(), code, token, expires_at.isoformat()))
        db.commit()
    return {"token": token, "code": code}

def verify_email_token_or_code(email: str, token_or_code: str) -> bool:
    """Verifies email verification token/code and marks user as verified."""
    import re
    clean_email = email.strip().lower()
    clean_val = re.sub(r'[^0-9A-Za-z]', '', token_or_code.strip())

    if not clean_val or not clean_email:
        return False

    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, expires_at FROM email_verifications
            WHERE LOWER(email) = ? AND (code = ? OR token = ?) AND verified_at IS NULL
            ORDER BY id DESC LIMIT 1
        """, (clean_email, clean_val, clean_val))
        row = cursor.fetchone()
        if not row:
            return False

        # Expiration check
        if row.get('expires_at'):
            try:
                exp_val = row['expires_at']
                if isinstance(exp_val, str):
                    exp_dt = datetime.fromisoformat(exp_val.replace('Z', '+00:00').split('+')[0])
                else:
                    exp_dt = exp_val
                if hasattr(exp_dt, 'tzinfo') and exp_dt.tzinfo:
                    exp_dt = exp_dt.replace(tzinfo=None)
                if datetime.utcnow() > exp_dt:
                    return False
            except Exception:
                pass

        # Mark verified in email_verifications table
        now_iso = datetime.utcnow().isoformat()
        cursor.execute("UPDATE email_verifications SET verified_at = ? WHERE id = ?", (now_iso, row['id']))
        # Mark verified in users table (cross-compatible boolean update)
        cursor.execute("UPDATE users SET is_verified = TRUE WHERE LOWER(email) = ?", (clean_email,))
        db.commit()
        return True

def get_pending_verification_code(email: str) -> Optional[Dict[str, Any]]:
    """Returns the most recent active unexpired verification code for an email, if any."""
    clean_email = email.strip().lower()
    with get_db_connection() as db:
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, code, token, expires_at, created_at 
            FROM email_verifications
            WHERE LOWER(email) = ? AND verified_at IS NULL
            ORDER BY id DESC LIMIT 1
        """, (clean_email,))
        row = cursor.fetchone()
        if not row:
            return None

        # Check if expired
        if row.get('expires_at'):
            try:
                exp_val = row['expires_at']
                if isinstance(exp_val, str):
                    exp_dt = datetime.fromisoformat(exp_val.replace('Z', '+00:00').split('+')[0])
                else:
                    exp_dt = exp_val
                if hasattr(exp_dt, 'tzinfo') and exp_dt.tzinfo:
                    exp_dt = exp_dt.replace(tzinfo=None)
                if datetime.utcnow() > exp_dt:
                    return None
            except Exception:
                pass
        return dict(row)

def direct_verify_email(email: str) -> bool:
    """Directly marks user email as verified (used for 1-click self-verification by authenticated user)."""
    clean_email = email.strip().lower()
    with get_db_connection() as db:
        cursor = db.cursor()
        now_iso = datetime.utcnow().isoformat()
        cursor.execute("UPDATE email_verifications SET verified_at = ? WHERE LOWER(email) = ? AND verified_at IS NULL", (now_iso, clean_email))
        cursor.execute("UPDATE users SET is_verified = TRUE WHERE LOWER(email) = ?", (clean_email,))
        db.commit()
        return True


