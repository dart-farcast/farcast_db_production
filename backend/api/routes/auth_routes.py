"""
FarCast DB v2 — Auth API Routes
Handles Registration, Login, Remember Me, Password Recovery, Email Verification,
Account Deactivation/Reactivation, Login History, and Security Notifications.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status
from pydantic import BaseModel, EmailStr
from ..auth import (
    get_db, hash_password, verify_password, create_access_token, decode_access_token,
    is_email_whitelisted, get_current_user,
    create_password_reset_token, verify_and_consume_reset_token,
    create_email_verification_token, verify_email_token_or_code,
    direct_verify_email, get_pending_verification_code,
    create_security_notification, get_user_notifications,
    mark_notification_as_read, mark_all_notifications_as_read,
    record_login_event, get_user_login_history, log_audit_event
)
from ..email_service import send_password_reset_email, send_verification_email, is_smtp_configured

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str
    remember_me: bool = False

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str

class VerifyEmailRequest(BaseModel):
    email: Optional[str] = None
    code: str

class ResendVerificationRequest(BaseModel):
    email: Optional[str] = None

class DeactivateRequest(BaseModel):
    password: str
    reason: Optional[str] = "User requested account deactivation"

class ReactivateRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

def get_client_ip(request: Request) -> str:
    """Extracts client IP from X-Forwarded-For or client host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ── Registration ─────────────────────────────────────────────────────────────

@router.post("/register")
def register(req: RegisterRequest, request: Request):
    email_clean = req.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    whitelisted = 1 if is_email_whitelisted(email_clean) else 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="An account with this email already exists.")

        hashed_pw = hash_password(req.password)
        cursor.execute("""
            INSERT INTO users (email, full_name, password_hash, role, is_whitelisted, is_active, is_verified)
            VALUES (?, ?, ?, 'user', ?, TRUE, FALSE)
        """, (email_clean, req.full_name.strip(), hashed_pw, bool(whitelisted)))
        conn.commit()

        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        u_row = cursor.fetchone()
        user_id = u_row["id"] if u_row else cursor.lastrowid

    # Create verification token & code
    verif = create_email_verification_token(email_clean)

    # Initial security notifications & audit log
    create_security_notification(
        email_clean,
        "Welcome to FarCast Data Portal",
        "Your account has been registered. Please verify your email to unlock all platform features.",
        "account"
    )
    log_audit_event(email_clean, "USER_REGISTER", f"Account created for {email_clean}")

    user_info = {
        "id": user_id,
        "email": email_clean,
        "full_name": req.full_name,
        "role": "user",
        "is_whitelisted": bool(whitelisted),
        "is_active": True,
        "is_verified": False,
        "allowed_studies": "*",
        "allowed_samples": "*",
        "can_download": False
    }

    token = create_access_token({"sub": email_clean, "role": "user", "is_whitelisted": bool(whitelisted)})
    return {
        "success": True,
        "token": token,
        "user": user_info,
        "verification_code": verif["code"],
        "message": "Account created successfully! Please verify your email." if whitelisted else "Account created. Awaiting admin whitelist approval."
    }


# ── Login ────────────────────────────────────────────────────────────────────

@router.post("/login")
def login(req: LoginRequest, request: Request):
    email_clean = req.email.strip().lower()
    ip_addr = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,))
        user = cursor.fetchone()

        if not user:
            record_login_event(email_clean, "FAILED", ip_addr, user_agent, "Account not found")
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        user_dict = dict(user)

        # Check account active status (Deactivation check)
        is_active = bool(user_dict.get("is_active", 1))
        if not is_active:
            record_login_event(email_clean, "BLOCKED", ip_addr, user_agent, "Account deactivated")
            raise HTTPException(
                status_code=403, 
                detail="Your account has been deactivated. You can reactivate your account below or contact an administrator."
            )

        # Verify password
        if not verify_password(req.password, user_dict["password_hash"]):
            failed_attempts = int(user_dict.get("failed_login_attempts", 0) or 0) + 1
            cursor.execute("UPDATE users SET failed_login_attempts = ? WHERE LOWER(email) = ?", (failed_attempts, email_clean))
            conn.commit()

            record_login_event(email_clean, "FAILED", ip_addr, user_agent, "Incorrect password")

            if failed_attempts >= 5:
                create_security_notification(
                    email_clean,
                    "⚠️ Multiple Failed Login Attempts",
                    f"Warning: {failed_attempts} failed login attempts detected from IP {ip_addr}.",
                    "security"
                )

            raise HTTPException(status_code=401, detail="Invalid email or password.")

        # Check / update whitelist status
        is_whitelisted = bool(user_dict.get("is_whitelisted", 0))
        if not is_whitelisted and is_email_whitelisted(email_clean):
            cursor.execute("UPDATE users SET is_whitelisted = TRUE WHERE LOWER(email) = ?", (email_clean,))
            is_whitelisted = True

        # Successful login: reset failed attempts & update last login
        cursor.execute("""
            UPDATE users 
            SET last_login = ?, failed_login_attempts = 0 
            WHERE LOWER(email) = ?
        """, (datetime.utcnow().isoformat(), email_clean))
        conn.commit()

    # Record login history event
    record_login_event(email_clean, "SUCCESS", ip_addr, user_agent)

    # Determine token duration based on Remember Me
    expires_delta = timedelta(days=30) if req.remember_me else timedelta(days=1)

    raw_studies = user_dict.get("allowed_studies", "*")
    if raw_studies != "*" and isinstance(raw_studies, str):
        allowed_studies = [s.strip() for s in raw_studies.split(",") if s.strip()]
    else:
        allowed_studies = "*"

    raw_samples = user_dict.get("allowed_samples", "*")
    if raw_samples != "*" and isinstance(raw_samples, str):
        allowed_samples = [s.strip() for s in raw_samples.split(",") if s.strip()]
    else:
        allowed_samples = "*"

    can_download = bool(user_dict.get("can_download", 0)) or user_dict.get("role") == "admin"
    is_verified = bool(user_dict.get("is_verified", 0))

    token_data = {
        "sub": email_clean,
        "id": user_dict["id"],
        "role": user_dict["role"],
        "is_whitelisted": bool(is_whitelisted),
        "remember_me": req.remember_me
    }
    token = create_access_token(token_data, expires_delta=expires_delta)

    return {
        "success": True,
        "token": token,
        "remember_me": req.remember_me,
        "expires_in_days": 30 if req.remember_me else 1,
        "user": {
            "id": user_dict["id"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "role": user_dict["role"],
            "is_whitelisted": bool(is_whitelisted),
            "is_active": True,
            "is_verified": is_verified,
            "allowed_studies": allowed_studies,
            "allowed_samples": allowed_samples,
            "can_download": can_download
        }
    }


# ── Password Recovery ────────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    email_clean = req.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email_clean,))
        user = cursor.fetchone()
        if not user:
            # Prevent email enumeration while giving clear response
            return {
                "success": True,
                "email_dispatched": True,
                "message": f"If an account is registered with {email_clean}, a 6-digit recovery code has been sent to the email address."
            }

    res = create_password_reset_token(email_clean)
    code = res["code"]

    create_security_notification(
        email_clean,
        "🔑 Password Recovery Requested",
        f"A password reset code was requested for your account. Code: {code} (Valid for 1 hour).",
        "password"
    )
    log_audit_event(email_clean, "FORGOT_PASSWORD", f"Password reset requested for {email_clean}")

    # Dispatch email via SMTP
    email_sent, email_msg = send_password_reset_email(email_clean, code)

    response_data = {
        "success": True,
        "email_dispatched": email_sent,
    }

    if email_sent:
        response_data["message"] = f"A 6-digit recovery code has been sent to {email_clean}. Please check your inbox and spam folder."
    else:
        print(f"  [Forgot Password Notice] Email delivery failed or SMTP unconfigured: {email_msg}")
        if is_smtp_configured():
            response_data["message"] = f"Failed to deliver email to {email_clean}: {email_msg}"
        else:
            response_data["message"] = f"SMTP is not configured in .env. Recovery code: {code}"
            # Fallback code for development / unconfigured SMTP environment
            response_data["reset_code"] = code

    return response_data

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    email_clean = req.email.strip().lower()
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

    hashed_pw = hash_password(req.new_password)
    success = verify_and_consume_reset_token(email_clean, req.token.strip(), hashed_pw)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code / token. Please request a new one.")

    create_security_notification(
        email_clean,
        "🔒 Password Reset Successful",
        "Your account password was successfully reset. You can now sign in with your new credentials.",
        "password"
    )
    log_audit_event(email_clean, "PASSWORD_RESET_COMPLETED", f"Password successfully reset for {email_clean}")

    return {
        "success": True,
        "message": "Password reset successful! Please sign in with your new password."
    }


# ── User Profile & Email Verification ─────────────────────────────────────────

def send_verification_email_notification(email: str, code: str) -> bool:
    """Dispatches in-app security notification and attempts SMTP delivery."""
    create_security_notification(
        email,
        "🔑 Email Verification Code",
        f"Your FarCast account confirmation code is: {code} (Valid for 24 hours).",
        "account"
    )
    email_sent, _ = send_verification_email(email, code)
    return email_sent


@router.get("/me")
def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Returns the current fresh authenticated user profile and any active pending verification code."""
    email_clean = current_user["email"].strip().lower()
    pending = get_pending_verification_code(email_clean) if not current_user.get("is_verified") else None
    return {
        "success": True,
        "user": current_user,
        "pending_verification": {
            "has_pending": bool(pending),
            "code": pending["code"] if pending else None,
            "expires_at": pending["expires_at"] if pending else None
        } if pending else None
    }


@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, request: Request):
    # If Bearer token is provided, infer email if not explicitly sent
    auth_header = request.headers.get("Authorization", "")
    inferred_email = None
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header.split(" ")[1])
            inferred_email = payload.get("sub")
        except Exception:
            pass

    target_email = (req.email or inferred_email or "").strip().lower()
    if not target_email or "@" not in target_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    code_clean = req.code.strip()
    if not code_clean:
        raise HTTPException(status_code=400, detail="Verification code is required.")

    success = verify_email_token_or_code(target_email, code_clean)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code. Please request a new one.")

    create_security_notification(
        target_email,
        "✅ Email Ownership Verified",
        "Your email address has been successfully confirmed and verified.",
        "account"
    )
    log_audit_event(target_email, "EMAIL_VERIFIED", f"Email address {target_email} confirmed")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, full_name, role, is_whitelisted, is_active, is_verified FROM users WHERE LOWER(email) = ?", (target_email,))
        updated_user = cursor.fetchone()

    return {
        "success": True,
        "message": "Email ownership confirmed successfully!",
        "user": dict(updated_user) if updated_user else None
    }


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, request: Request):
    auth_header = request.headers.get("Authorization", "")
    inferred_email = None
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header.split(" ")[1])
            inferred_email = payload.get("sub")
        except Exception:
            pass

    email_clean = (req.email or inferred_email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="A valid email address is required.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_verified FROM users WHERE LOWER(email) = ?", (email_clean,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Account not found.")
        if bool(dict(user).get("is_verified", 0)):
            return {"success": True, "message": "Email is already verified.", "is_verified": True}

    res = create_email_verification_token(email_clean)
    code = res["code"]
    email_dispatched = send_verification_email_notification(email_clean, code)

    response_data = {
        "success": True,
        "email_dispatched": email_dispatched,
    }
    if email_dispatched:
        response_data["message"] = f"A 6-digit verification code has been dispatched to {email_clean}. Please check your inbox."
        response_data["note"] = "Code sent to your email and in-app Notifications Bell."
    else:
        if is_smtp_configured():
            response_data["message"] = f"Mail delivery failed. Code logged to in-app Notifications Bell."
        else:
            response_data["message"] = f"SMTP is not configured in .env. Verification code: {code}"
            response_data["verification_code"] = code
        response_data["note"] = "Code dispatched to your in-app Notifications Bell."

    return response_data


@router.post("/verify-email-instant")
def verify_email_instant(current_user: dict = Depends(get_current_user)):
    """Allows an authenticated user to immediately confirm account ownership with 1-click."""
    email_clean = current_user["email"].strip().lower()
    direct_verify_email(email_clean)

    create_security_notification(
        email_clean,
        "✅ Email Ownership Confirmed",
        "Your account email was confirmed via authenticated instant verification.",
        "account"
    )
    log_audit_event(email_clean, "EMAIL_VERIFIED_INSTANT", f"Instant email confirmation for {email_clean}")

    return {
        "success": True,
        "message": f"Email {email_clean} has been confirmed successfully!",
        "user": {
            **current_user,
            "is_verified": True
        }
    }



# ── Account Deactivation & Reactivation ──────────────────────────────────────

@router.post("/deactivate")
def deactivate_account(req: DeactivateRequest, current_user: dict = Depends(get_current_user)):
    email_clean = current_user["email"].strip().lower()

    # Re-verify password for safety
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Incorrect password. Account deactivation cancelled.")

        now_iso = datetime.utcnow().isoformat()
        cursor.execute("""
            UPDATE users 
            SET is_active = FALSE, deactivated_at = ?, deactivation_reason = ? 
            WHERE LOWER(email) = ?
        """, (now_iso, req.reason or "User self-deactivation", email_clean))
        conn.commit()

    create_security_notification(
        email_clean,
        "⚠️ Account Deactivated",
        f"Your account has been deactivated. Reason: {req.reason}",
        "security"
    )
    log_audit_event(email_clean, "ACCOUNT_DEACTIVATED", f"User self-deactivated account: {req.reason}")

    return {
        "success": True,
        "message": "Your account has been deactivated. You can reactivate anytime using your credentials."
    }

@router.post("/reactivate")
def reactivate_account(req: ReactivateRequest):
    email_clean = req.email.strip().lower()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash, is_active FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        if not row or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Invalid email or password.")

        cursor.execute("""
            UPDATE users 
            SET is_active = TRUE, deactivated_at = NULL, deactivation_reason = NULL 
            WHERE LOWER(email) = ?
        """, (email_clean,))
        conn.commit()

    create_security_notification(
        email_clean,
        "🎉 Account Reactivated",
        "Welcome back! Your FarCast Data Portal account has been restored and reactivated.",
        "account"
    )
    log_audit_event(email_clean, "ACCOUNT_REACTIVATED", f"User restored account: {email_clean}")

    return {
        "success": True,
        "message": "Account reactivated successfully! You may now sign in."
    }


# ── Password Change (Logged in User) ─────────────────────────────────────────

@router.post("/change-password")
def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    email_clean = current_user["email"].strip().lower()
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE LOWER(email) = ?", (email_clean,))
        row = cursor.fetchone()
        if not row or not verify_password(req.current_password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password incorrect.")

        now_iso = datetime.utcnow().isoformat()
        new_hashed = hash_password(req.new_password)
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, last_password_change = ? 
            WHERE LOWER(email) = ?
        """, (new_hashed, now_iso, email_clean))
        conn.commit()

    create_security_notification(
        email_clean,
        "🛡️ Password Updated",
        "Your account password was successfully changed from Account Settings.",
        "password"
    )
    log_audit_event(email_clean, "PASSWORD_CHANGED", f"User changed password from settings")

    return {
        "success": True,
        "message": "Password updated successfully."
    }


# ── Login History & Security Notifications ───────────────────────────────────

@router.get("/login-history")
def get_my_login_history(current_user: dict = Depends(get_current_user)):
    history = get_user_login_history(current_user["email"], limit=25)
    return {
        "success": True,
        "history": [dict(h) for h in history]
    }

@router.get("/notifications")
def get_my_notifications(current_user: dict = Depends(get_current_user)):
    notifications = get_user_notifications(current_user["email"], limit=30)
    return {
        "success": True,
        "notifications": [dict(n) for n in notifications]
    }

@router.patch("/notifications/{notification_id}/read")
def read_notification(notification_id: int, current_user: dict = Depends(get_current_user)):
    success = mark_notification_as_read(notification_id, current_user["email"])
    return {"success": success}

@router.post("/notifications/read-all")
def read_all_notifications(current_user: dict = Depends(get_current_user)):
    count = mark_all_notifications_as_read(current_user["email"])
    return {"success": True, "count": count}

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "user": current_user
    }


