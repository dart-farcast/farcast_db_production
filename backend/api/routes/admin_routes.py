from typing import Optional, List, Union
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from ..auth import get_db, get_current_admin_user, is_email_whitelisted
from ..cache import cache

router = APIRouter(prefix="/admin", tags=["admin"])

class AddWhitelistRequest(BaseModel):
    pattern: str
    notes: Optional[str] = ""

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    is_whitelisted: Optional[bool] = None
    allowed_studies: Optional[Union[List[str], str]] = None

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
            SELECT id, email, full_name, role, is_whitelisted, allowed_studies, created_at, last_login
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

        user_list.append({
            "id": u_dict["id"],
            "email": u_dict["email"],
            "full_name": u_dict["full_name"],
            "role": u_dict["role"],
            "is_whitelisted": bool(u_dict["is_whitelisted"]),
            "allowed_studies": allowed_studies,
            "created_at": u_dict["created_at"],
            "last_login": u_dict["last_login"]
        })
    return {
        "success": True,
        "users": user_list
    }


@router.patch("/users/{user_id}")
def update_user(user_id: int, req: UpdateUserRequest, current_admin: dict = Depends(get_current_admin_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, role, is_whitelisted, allowed_studies FROM users WHERE id = ?", (user_id,))
        target_user = cursor.fetchone()
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found.")

        target_dict = dict(target_user)
        updates = []
        params = []

        if req.role is not None and req.role in ['admin', 'user']:
            updates.append("role = ?")
            params.append(req.role)

        if req.is_whitelisted is not None:
            updates.append("is_whitelisted = ?")
            params.append(bool(req.is_whitelisted))

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

        if not updates:
            raise HTTPException(status_code=400, detail="No valid update fields provided.")

        params.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

    log_audit(current_admin["email"], "UPDATE_USER", 
              f"Updated user ID {user_id} ({target_dict['email']}): role={req.role}, whitelisted={req.is_whitelisted}, allowed_studies={req.allowed_studies}")

    return {
        "success": True,
        "message": f"User {target_dict['email']} updated successfully."
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


