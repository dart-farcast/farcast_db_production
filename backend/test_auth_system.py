"""
FarCast DB v2 — Auth & Whitelist System Verification Script
"""
import sys
import time
from fastapi.testclient import TestClient
from app import app

def test_full_auth_flow():
    with TestClient(app) as client:
        ts = int(time.time())
        unwhitelisted_email = f"guest_{ts}@external.org"
        domain_email = f"scientist_{ts}@farcastbio.com"

        print("\n--- 1. Testing Default Admin Login ---")
        res = client.post("/api/auth/login", json={"email": "admin@farcastbio.com", "password": "admin123"})
        if res.status_code != 200:
            res = client.post("/api/auth/login", json={"email": "admin@farcast.com", "password": "admin123"})
        assert res.status_code == 200, f"Login failed: {res.text}"
        admin_data = res.json()
        admin_token = admin_data["token"]
        assert admin_data["user"]["role"] == "admin"
        assert admin_data["user"]["is_whitelisted"] == True
        print("[OK] Admin login successful.")

        print("\n--- 2. Testing Unauthenticated Request to Protected Route ---")
        res = client.get("/api/stats")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("[OK] Unauthenticated request properly rejected with HTTP 401.")

        print("\n--- 3. Testing Non-Whitelisted User Registration ---")
        res = client.post("/api/auth/register", json={
            "email": unwhitelisted_email,
            "password": "guestpassword123",
            "full_name": "Dr. Guest"
        })
        assert res.status_code == 200, f"Registration failed: {res.text}"
        reg_data = res.json()
        guest_token = reg_data["token"]
        assert reg_data["user"]["is_whitelisted"] == False
        print("[OK] Non-whitelisted user registered with pending whitelist status.")

        print("\n--- 4. Testing Non-Whitelisted User Access to Database ---")
        res = client.get("/api/stats", headers={"Authorization": f"Bearer {guest_token}"})
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"
        print("[OK] Non-whitelisted user blocked from accessing database routes with HTTP 403.")

        print("\n--- 5. Testing Domain-Based Auto-Whitelisting Registration ---")
        res = client.post("/api/auth/register", json={
            "email": domain_email,
            "password": "sciencestudio",
            "full_name": "FarCast Scientist"
        })
        assert res.status_code == 200, f"Domain registration failed: {res.text}"
        sci_data = res.json()
        sci_token = sci_data["token"]
        assert sci_data["user"]["is_whitelisted"] == True
        print("[OK] Company domain email (@farcastbio.com) auto-whitelisted upon registration.")

        print("\n--- 6. Testing Whitelisted User Search Database Route ---")
        res = client.get("/api/stats", headers={"Authorization": f"Bearer {sci_token}"})
        assert res.status_code == 200, f"Expected 200, got {res.text}"
        print("[OK] Whitelisted user granted database access.")

        print("\n--- 7. Testing Admin Whitelisting the Pending Email ---")
        res = client.post("/api/admin/whitelist", 
                          json={"pattern": unwhitelisted_email, "notes": "Approved by Dr. Admin"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Whitelisting failed: {res.text}"
        print("[OK] Admin successfully whitelisted guest email.")

        print("\n--- 8. Testing Previously Pending User Access After Admin Whitelist ---")
        res = client.post("/api/auth/login", json={"email": unwhitelisted_email, "password": "guestpassword123"})
        assert res.status_code == 200, f"Re-login failed: {res.text}"
        new_guest_token = res.json()["token"]
        assert res.json()["user"]["is_whitelisted"] == True

        res = client.get("/api/stats", headers={"Authorization": f"Bearer {new_guest_token}"})
        assert res.status_code == 200, f"Database fetch failed: {res.text}"
        print("[OK] Approved user now successfully accesses the database.")

        print("\n=== ALL AUTHENTICATION AND ADMIN WHITELIST TESTS PASSED SUCCESSFULLY! ===\n")

if __name__ == "__main__":
    test_full_auth_flow()
