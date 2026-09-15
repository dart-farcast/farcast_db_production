"""
FarCast DB v2 — Auth API Routes
Handles Registration, Login, Profile retrieval.
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from ..auth import (
    get_db, hash_password, verify_password, create_access_token,
    is_email_whitelisted, get_current_user
)

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
def register(req: RegisterRequest):
    email_clean = req.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Invalid email address.")
    
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    whitelisted = 1 if is_email_whitelisted(email_clean) else 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="An account with this email already exists.")

        hashed_pw = hash_password(req.password)
        cursor.execute("""
            INSERT INTO users (email, full_name, password_hash, role, is_whitelisted)
            VALUES (?, ?, ?, 'user', ?)
        """, (email_clean, req.full_name.strip(), hashed_pw, bool(whitelisted)))
        conn.commit()

        user_id = cursor.lastrowid

    user_info = {
        "id": user_id,
        "email": email_clean,
        "full_name": req.full_name,
        "role": "user",
        "is_whitelisted": bool(whitelisted),
        "allowed_studies": "*"
    }

    token = create_access_token({"sub": email_clean, "role": "user", "is_whitelisted": bool(whitelisted)})
    return {
        "success": True,
        "token": token,
        "user": user_info,
        "message": "Account created successfully!" if whitelisted else "Account created. Awaiting admin whitelist approval."
    }

@router.post("/login")
def login(req: LoginRequest):
    email_clean = req.email.strip().lower()
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email_clean,))
        user = cursor.fetchone()

        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        user_dict = dict(user)

        # Check / update whitelist status
        is_whitelisted = user_dict["is_whitelisted"]
        if not is_whitelisted and is_email_whitelisted(email_clean):
            cursor.execute("UPDATE users SET is_whitelisted = TRUE WHERE email = ?", (email_clean,))
            is_whitelisted = True


        # Update last login
        cursor.execute("UPDATE users SET last_login = ? WHERE email = ?", 
                       (datetime.utcnow().isoformat(), email_clean))
        conn.commit()

    raw_studies = user_dict.get("allowed_studies", "*")
    if raw_studies != "*" and isinstance(raw_studies, str):
        allowed_studies = [s.strip() for s in raw_studies.split(",") if s.strip()]
    else:
        allowed_studies = "*"

    token_data = {
        "sub": email_clean,
        "id": user_dict["id"],
        "role": user_dict["role"],
        "is_whitelisted": bool(is_whitelisted)
    }
    token = create_access_token(token_data)

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_dict["id"],
            "email": user_dict["email"],
            "full_name": user_dict["full_name"],
            "role": user_dict["role"],
            "is_whitelisted": bool(is_whitelisted),
            "allowed_studies": allowed_studies
        }
    }

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "user": current_user
    }

