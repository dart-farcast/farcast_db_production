from typing import Optional, List, Union
import secrets
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from ..auth import (
    get_db, get_current_admin_user, is_email_whitelisted,
    hash_password, create_security_notification,
    get_all_login_history, get_user_login_history
)
from ..cache import cache

router = APIRouter(prefix="/admin", tags=["admin"])

class AddWhitelistRequest(BaseModel):
    pattern: str
    notes: Optional[str] = ""

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_whitelisted: Optional[bool] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    allowed_studies: Optional[Union[List[str], str]] = None
    allowed_samples: Optional[Union[List[str], str]] = None
    can_download: Optional[bool] = None

class InviteUserRequest(BaseModel):
    email: str
    full_name: Optional[str] = ""
    role: Optional[str] = "user"
    allowed_studies: Optional[Union[List[str], str]] = "*"
    allowed_samples: Optional[Union[List[str], str]] = "*"
    can_download: Optional[bool] = False
    temporary_password: Optional[str] = None

class AdminResetPasswordRequest(BaseModel):
    new_password: Optional[str] = None

def log_audit(actor_email: str, action: str, details: str):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO audit_logs (actor_email, action, details) VALUES (?, ?, ?)",
                           (actor_email, action, details))
            conn.commit()
    except Exception:
        pass

@router.get("/whitelist")
def list_whitelisted_emails(current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM whitelisted_emails ORDER BY id DESC")
        rows = cursor.fetchall()
        return {
            "success": True,
            "whitelist": [dict(r) for r in rows]
        }

@router.post("/whitelist")
def add_to_whitelist(req: AddWhitelistRequest, current_admin: dict = Depends(get_current_admin_user)):
    pattern_clean = req.pattern.strip().lower()
    if not pattern_clean:
        raise HTTPException(status_code=400, detail="Whitelist pattern cannot be empty.")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO whitelisted_emails (pattern, added_by, notes) VALUES (?, ?, ?)",
                (pattern_clean, current_admin["email"], req.notes or "")
            )
            conn.commit()
        except Exception:
            raise HTTPException(status_code=400, detail="This email or pattern is already whitelisted.")

        # Automatically whitelist matching registered users
        if pattern_clean.startswith("@"):
            cursor.execute("UPDATE users SET is_whitelisted = TRUE WHERE LOWER(email) LIKE ?", 
                           (f"%{pattern_clean}",))
        else:
            cursor.execute("UPDATE users SET is_whitelisted = TRUE WHERE LOWER(email) = ?", 
                           (pattern_clean,))
        conn.commit()

    log_audit(current_admin["email"], "ADD_WHITELIST", f"Added '{pattern_clean}' to whitelist.")

    return {
        "success": True,
        "message": f"Successfully whitelisted '{pattern_clean}'."
    }

@router.delete("/whitelist/{pattern:path}")
def remove_from_whitelist(pattern: str, current_admin: dict = Depends(get_current_admin_user)):
    pattern_clean = pattern.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whitelisted_emails WHERE pattern = ?", (pattern_clean,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Whitelist entry not found.")
        conn.commit()

        # Re-evaluate non-admin users' whitelist status
        cursor.execute("SELECT id, email FROM users WHERE role != 'admin'")
        non_admins = cursor.fetchall()
        for u in non_admins:
            wl_status = bool(is_email_whitelisted(u['email']))
            cursor.execute("UPDATE users SET is_whitelisted = ? WHERE id = ?", (wl_status, u['id']))
        conn.commit()

    log_audit(current_admin["email"], "REMOVE_WHITELIST", f"Removed '{pattern_clean}' from whitelist.")

    return {
        "success": True,
        "message": f"Removed '{pattern_clean}' from whitelist."
    }

@router.get("/available_studies")
def list_available_studies(current_admin: dict = Depends(get_current_admin_user)):
    """Returns all unique study names present in the dataset."""
    studies = cache.stats.get("study_list", [])
    if not studies and cache.indexes.get("study"):
        studies = sorted([s.title() for s in cache.indexes["study"].keys()])
    return {
        "success": True,
        "studies": studies
    }

@router.get("/users")
def list_users(current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, full_name, role, is_whitelisted, is_active, is_verified,
                   allowed_studies, allowed_samples, can_download, deactivated_at,
                   deactivation_reason, created_at, last_login
            FROM users
            ORDER BY id ASC
        """)
        users = cursor.fetchall()

    user_list = []
    for u in users:
        u_dict = dict(u)
        raw_studies = u_dict.get("allowed_studies", "*")
        if raw_studies != "*" and isinstance(raw_studies, str):
            allowed_studies = [s.strip() for s in raw_studies.split(",") if s.strip()]
        else:
            allowed_studies = "*"

        raw_samples = u_dict.get("allowed_samples", "*")
        if raw_samples != "*" and isinstance(raw_samples, str):
            allowed_samples = [s.strip() for s in raw_samples.split(",") if s.strip()]
        else:
            allowed_samples = "*"

        can_download = bool(u_dict.get("can_download", 0)) or u_dict["role"] == "admin"

        user_list.append({
            "id": u_dict["id"],
            "email": u_dict["email"],
            "full_name": u_dict["full_name"],
            "role": u_dict["role"],
            "is_whitelisted": bool(u_dict.get("is_whitelisted", 0)),
            "is_active": bool(u_dict.get("is_active", 1)),
            "is_verified": bool(u_dict.get("is_verified", 0)),
            "allowed_studies": allowed_studies,
            "allowed_samples": allowed_samples,
            "can_download": can_download,
            "deactivated_at": u_dict.get("deactivated_at"),
            "deactivation_reason": u_dict.get("deactivation_reason"),
            "created_at": u_dict["created_at"],
            "last_login": u_dict["last_login"]
        })
    return {
        "success": True,
        "users": user_list
    }

@router.post("/invite")
def invite_user(req: InviteUserRequest, current_admin: dict = Depends(get_current_admin_user)):
    """Allows an administrator to securely create/invite a user with designated role and permissions."""
    email_clean = req.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    role = req.role if req.role in ['admin', 'manager', 'analyst', 'user'] else 'user'
    temp_password = req.temporary_password.strip() if req.temporary_password else secrets.token_urlsafe(9)
    hashed_pw = hash_password(temp_password)

    # Process allowed studies
    if isinstance(req.allowed_studies, list):
        studies_val = '*' if ('*' in req.allowed_studies or len(req.allowed_studies) == 0) else ','.join(req.allowed_studies)
    else:
        studies_val = str(req.allowed_studies).strip() or '*'

    # Process allowed samples
    if isinstance(req.allowed_samples, list):
        samples_val = '*' if ('*' in req.allowed_samples or len(req.allowed_samples) == 0) else ','.join([s.strip() for s in req.allowed_samples if s.strip()])
    else:
        samples_val = str(req.allowed_samples).strip() or '*'

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"User with email '{email_clean}' already exists.")

        cursor.execute("""
            INSERT INTO users (email, full_name, password_hash, role, is_whitelisted, is_active, is_verified, allowed_studies, allowed_samples, can_download)
            VALUES (?, ?, ?, ?, TRUE, TRUE, TRUE, ?, ?, ?)
        """, (email_clean, req.full_name.strip(), hashed_pw, role, studies_val, samples_val, int(bool(req.can_download))))
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        row_id = cursor.fetchone()
        user_id = row_id["id"] if row_id else cursor.lastrowid

        # Also auto-whitelist email pattern if not present
        try:
            cursor.execute("INSERT INTO whitelisted_emails (pattern, added_by, notes) VALUES (?, ?, ?)",
                           (email_clean, current_admin["email"], f"Invited user account ({role})"))
            conn.commit()
        except Exception:
            pass

    log_audit(current_admin["email"], "INVITE_USER", f"Invited user {email_clean} with role '{role}'")
    create_security_notification(
        email_clean,
        "🎉 Welcome to FarCast Platform",
        f"You have been invited by {current_admin['email']} with the role '{role}'.",
        "account"
    )

    return {
        "success": True,
        "message": f"User '{email_clean}' successfully created & whitelisted.",
        "user_id": user_id,
        "email": email_clean,
        "role": role,
        "temporary_password": temp_password
    }

@router.patch("/users/{user_id}")
def update_user(user_id: int, req: UpdateUserRequest, current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, role, is_whitelisted, is_active, is_verified, 
                   allowed_studies, allowed_samples, can_download 
            FROM users WHERE id = ?
        """, (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found.")

        target_dict = dict(target_user)
        updates = []
        params = []

        if req.role is not None and req.role in ['admin', 'manager', 'analyst', 'user']:
            updates.append("role = ?")
            params.append(req.role)

        if req.is_whitelisted is not None:
            updates.append("is_whitelisted = ?")
            params.append(bool(req.is_whitelisted))

        if req.is_active is not None:
            updates.append("is_active = ?")
            params.append(bool(req.is_active))
            if not req.is_active:
                updates.append("deactivated_at = ?")
                params.append(datetime.utcnow().isoformat())
                updates.append("deactivation_reason = ?")
                params.append(f"Suspended by administrator {current_admin['email']}")
            else:
                updates.append("deactivated_at = NULL")
                updates.append("deactivation_reason = NULL")

        if req.is_verified is not None:
            updates.append("is_verified = ?")
            params.append(bool(req.is_verified))

        if req.allowed_studies is not None:
            if isinstance(req.allowed_studies, list):
                if '*' in req.allowed_studies or len(req.allowed_studies) == 0:
                    val = '*'
                else:
                    val = ','.join(req.allowed_studies)
            else:
                val = str(req.allowed_studies).strip()
            updates.append("allowed_studies = ?")
            params.append(val)

        if req.allowed_samples is not None:
            if isinstance(req.allowed_samples, list):
                if '*' in req.allowed_samples or len(req.allowed_samples) == 0:
                    val = '*'
                else:
                    val = ','.join([s.strip() for s in req.allowed_samples if s.strip()])
            else:
                val = str(req.allowed_samples).strip()
            updates.append("allowed_samples = ?")
            params.append(val)

        if req.can_download is not None:
            updates.append("can_download = ?")
            params.append(int(bool(req.can_download)))

        if not updates:
            raise HTTPException(status_code=400, detail="No valid update fields provided.")

        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    log_audit(current_admin["email"], "UPDATE_USER", 
              f"Updated user ID {user_id} ({target_dict['email']}): role={req.role}, active={req.is_active}, verified={req.is_verified}, whitelisted={req.is_whitelisted}")

    create_security_notification(
        target_dict['email'],
        "🛡️ Account Settings Updated",
        f"Your account status and permissions were updated by administrator {current_admin['email']}.",
        "security"
    )

    return {
        "success": True,
        "message": f"User {target_dict['email']} updated successfully."
    }

@router.post("/users/{user_id}/reset-password")
def admin_reset_user_password(user_id: int, req: AdminResetPasswordRequest, current_admin: dict = Depends(get_current_admin_user)):
    """Administrator triggers password reset or generates temporary password for user."""
    temp_password = req.new_password.strip() if req.new_password else secrets.token_urlsafe(9)
    if len(temp_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User account not found.")

        target_email = row['email']
        hashed_pw = hash_password(temp_password)
        now_iso = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, failed_login_attempts = 0, last_password_change = ? 
            WHERE id = ?
        """, (hashed_pw, now_iso, user_id))
        conn.commit()

    log_audit(current_admin["email"], "ADMIN_RESET_PASSWORD", f"Administrator reset password for user {target_email}")
    create_security_notification(
        target_email,
        "🔒 Account Password Reset",
        f"Your account password was reset by administrator {current_admin['email']}.",
        "password"
    )

    return {
        "success": True,
        "message": f"Password reset successfully for '{target_email}'.",
        "temporary_password": temp_password
    }

@router.get("/users/{user_id}/login-history")
def get_user_logins(user_id: int, current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found.")
        email = row['email']

    history = get_user_login_history(email, limit=50)
    return {
        "success": True,
        "email": email,
        "history": [dict(h) for h in history]
    }

@router.get("/login-history")
def get_global_login_history(current_admin: dict = Depends(get_current_admin_user)):
    history = get_all_login_history(limit=100)
    return {
        "success": True,
        "history": [dict(h) for h in history]
    }

@router.delete("/users/{user_id}")
def delete_user(user_id: int, current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="User account not found.")

        target_dict = dict(target_user)

        # Prevent admin from deleting their own active session account
        if target_dict["id"] == current_admin["id"]:
            raise HTTPException(status_code=400, detail="You cannot delete your own logged-in admin account.")

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()

    log_audit(current_admin["email"], "DELETE_USER", f"Permanently deleted user ID {user_id} ({target_dict['email']})")

    return {
        "success": True,
        "message": f"User account {target_dict['email']} has been permanently deleted."
    }

@router.get("/audit_logs")
def get_audit_logs(current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 50")
        logs = cursor.fetchall()
        return {
            "success": True,
            "logs": [dict(l) for l in logs]
        }

from fastapi.concurrency import run_in_threadpool
from ..cache import reload_cache

@router.post("/sync_database")
async def sync_database(current_admin: dict = Depends(get_current_admin_user)):
    import traceback
    err = None
    try:
        await run_in_threadpool(reload_cache)
        log_audit(current_admin["email"], "SYNC_DATABASE", "Manually triggered database synchronization and cache reload from Supabase.")
    except Exception as e:
        err = f"{e}\n{traceback.format_exc()}"
        return {
            "success": False,
            "error": err
        }

    return {
        "success": True,
        "message": "Database cache successfully synchronized from Supabase.",
        "stats": cache.stats,
        "meta_len": len(cache.metadata),
        "overlay_len": len(cache.overlay),
        "assays": {k: len(v) for k, v in cache.assay_dfs.items()}
    }




