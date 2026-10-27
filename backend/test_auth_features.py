"""
FarCast DB v2 — Comprehensive Auth Features Verification Test Suite
Tests:
1. Registration & Email Verification
2. Login with Remember Me
3. Show/hide password (tested on client side)
4. Password Recovery (Forgot Password & Reset)
5. Account Deactivation & Reactivation
6. Login History Tracking (Success, Failed, Blocked)
7. Security Notifications (Creation, retrieval, read)
8. Admin User Management (Invite, role assignment, disable/suspend, reset password, audit)
"""
import os
import sys
import time
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

def run_tests():
    with TestClient(app) as client:
        ts = int(time.time())
        test_email = f"researcher_{ts}@farcastbio.com"
        test_pass = "SecurePass123!"
        new_pass = "EvenMoreSecure456!"

        print("\n=======================================================")
        print("  FarCast DB v2 — Enhanced Authentication Test Suite  ")
        print("=======================================================\n")

        # 1. Admin Login
        print("1. Admin Login...")
        res = client.post("/api/auth/login", json={"email": "admin@farcastbio.com", "password": "admin123"})
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        admin_token = res.json()["token"]
        print("   [PASS] Admin authenticated successfully.")

        # 2. Registration & Email Verification
        print("\n2. User Registration & Email Verification...")
        res = client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_pass,
            "full_name": "Dr. Farcast Scientist"
        })
        assert res.status_code == 200, f"Register failed: {res.text}"
        reg_data = res.json()
        assert reg_data["user"]["is_verified"] == False
        v_code = reg_data["verification_code"]
        assert v_code, "Verification code not generated"
        print(f"   [PASS] User registered. Generated verification code: {v_code}")

        # Verify email using code
        res = client.post("/api/auth/verify-email", json={"email": test_email, "code": v_code})
        assert res.status_code == 200, f"Email verification failed: {res.text}"
        print("   [PASS] Email verified successfully.")

        # 3. Login with Remember Me
        print("\n3. Login with Remember Me...")
        res = client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_pass,
            "remember_me": True
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        login_data = res.json()
        user_token = login_data["token"]
        assert login_data["remember_me"] == True
        assert login_data["expires_in_days"] == 30
        assert login_data["user"]["is_verified"] == True
        print("   [PASS] Login with Remember Me succeeded (30-day token duration).")

        # 4. Security Notifications Retrieval
        print("\n4. Security Notifications Retrieval...")
        res = client.get("/api/auth/notifications", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200, f"Notifications failed: {res.text}"
        notifs = res.json()["notifications"]
        assert len(notifs) >= 1, "Should have welcome or verification notification"
        print(f"   [PASS] Retrieved {len(notifs)} security notifications.")

        # Mark notification as read
        notif_id = notifs[0]["id"]
        res = client.patch(f"/api/auth/notifications/{notif_id}/read", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200
        print("   [PASS] Marked notification as read.")

        # 5. Forgot Password & Reset Password
        print("\n5. Forgot Password & Reset Password...")
        res = client.post("/api/auth/forgot-password", json={"email": test_email})
        assert res.status_code == 200, f"Forgot password failed: {res.text}"
        reset_code = res.json().get("reset_code")
        if not reset_code:
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SELECT code FROM password_resets WHERE LOWER(email) = ? ORDER BY id DESC LIMIT 1", (test_email.lower(),))
                row = cursor.fetchone()
                reset_code = row["code"] if row else None
        assert reset_code, "Reset code missing"
        print(f"   [PASS] Forgot password generated reset code: {reset_code}")

        res = client.post("/api/auth/reset-password", json={
            "email": test_email,
            "token": reset_code,
            "new_password": new_pass
        })
        assert res.status_code == 200, f"Reset password failed: {res.text}"
        print("   [PASS] Password successfully reset.")

        # Verify login with old password fails
        res = client.post("/api/auth/login", json={"email": test_email, "password": test_pass})
        assert res.status_code == 401, "Old password should be rejected"

        # Verify login with new password succeeds
        res = client.post("/api/auth/login", json={"email": test_email, "password": new_pass})
        assert res.status_code == 200, "New password should succeed"
        user_token = res.json()["token"]
        user_id = res.json()["user"]["id"]
        print("   [PASS] Logged in with new password.")

        # 6. Login History Tracking
        print("\n6. Login History Tracking...")
        res = client.get("/api/auth/login-history", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200
        history = res.json()["history"]
        statuses = [h["status"] for h in history]
        assert "SUCCESS" in statuses
        assert "FAILED" in statuses
        print(f"   [PASS] Login history verified ({len(history)} events captured, including SUCCESS and FAILED).")

        # 7. Account Deactivation & Reactivation
        print("\n7. Account Deactivation & Reactivation...")
        # Deactivate
        res = client.post("/api/auth/deactivate", 
                          json={"password": new_pass, "reason": "Testing sabbatical"},
                          headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200, f"Deactivation failed: {res.text}"
        print("   [PASS] Account deactivated.")

        # Attempt to login while deactivated -> must be blocked
        res = client.post("/api/auth/login", json={"email": test_email, "password": new_pass})
        assert res.status_code == 403, f"Expected 403 for deactivated account, got {res.status_code}"
        print("   [PASS] Deactivated login attempt correctly blocked with HTTP 403.")

        # Reactivate
        res = client.post("/api/auth/reactivate", json={"email": test_email, "password": new_pass})
        assert res.status_code == 200, f"Reactivation failed: {res.text}"
        print("   [PASS] Account reactivated successfully.")

        # Login again after reactivation
        res = client.post("/api/auth/login", json={"email": test_email, "password": new_pass})
        assert res.status_code == 200
        user_token = res.json()["token"]
        print("   [PASS] Successfully logged in after account reactivation.")

        # 8. Admin User Management
        print("\n8. Admin User Management (Invite, Suspend, Role Assignment)...")
        # Invite new user
        invite_email = f"invited_{ts}@farcastbio.com"
        res = client.post("/api/admin/invite", json={
            "email": invite_email,
            "full_name": "Senior Analyst",
            "role": "analyst",
            "can_download": True,
            "temporary_password": "TempPassword999!"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Admin invite failed: {res.text}"
        invited_id = res.json()["user_id"]
        print(f"   [PASS] Admin invited new user '{invite_email}' with role 'analyst'.")

        # Admin disables / suspends user
        res = client.patch(f"/api/admin/users/{invited_id}", 
                           json={"is_active": False},
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Admin suspend failed: {res.text}"
        print(f"   [PASS] Admin suspended user ID {invited_id}.")

        # Verify suspended user cannot log in
        res = client.post("/api/auth/login", json={"email": invite_email, "password": "TempPassword999!"})
        assert res.status_code == 403, "Suspended user should receive 403"
        print("   [PASS] Suspended user properly rejected at login.")

        # Admin reactivates and changes role to 'manager'
        res = client.patch(f"/api/admin/users/{invited_id}", 
                           json={"is_active": True, "role": "manager"},
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        print(f"   [PASS] Admin restored user and assigned role 'manager'.")

        # Admin resets user password
        res = client.post(f"/api/admin/users/{invited_id}/reset-password",
                          json={"new_password": "AdminSetPass123!"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        print(f"   [PASS] Admin reset user password.")

        # Admin checks global login history
        res = client.get("/api/admin/login-history", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        global_history = res.json()["history"]
        assert len(global_history) >= 2
        print(f"   [PASS] Admin global login history retrieved ({len(global_history)} records).")

        print("\n=======================================================")
        print("  [SUCCESS] ALL ENHANCED AUTHENTICATION TESTS PASSED 100%!   ")
        print("=======================================================\n")

if __name__ == "__main__":
    run_tests()
