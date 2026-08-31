"""
FarCast DB v2 — Study-Level User Access Control (RBAC) Verification Test
"""
import sys
import time
from fastapi.testclient import TestClient
from app import app

def test_study_access_control():
    with TestClient(app) as client:
        ts = int(time.time())
        restricted_email = f"study_user_{ts}@external.org"
        password = "password123"

        print("\n--- 1. Login as Default Admin ---")
        res = client.post("/api/auth/login", json={"email": "admin@farcastbio.com", "password": "admin123"})
        if res.status_code != 200:
            res = client.post("/api/auth/login", json={"email": "admin@farcast.com", "password": "admin123"})
        assert res.status_code == 200, f"Admin login failed: {res.text}"
        admin_token = res.json()["token"]
        print("[OK] Admin login successful.")

        print("\n--- 2. Register New User ---")
        res = client.post("/api/auth/register", json={
            "email": restricted_email,
            "password": password,
            "full_name": "Dr. Scoped Researcher"
        })
        assert res.status_code == 200, f"Registration failed: {res.text}"
        user_id = res.json()["user"]["id"]
        user_token = res.json()["token"]
        print("[OK] User registered successfully.")

        print("\n--- 3. Admin Whitelists User and Assigns Allowed Study ('BioBank') ---")
        res = client.post("/api/admin/whitelist", 
                          json={"pattern": restricted_email, "notes": "RBAC Test User"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Whitelist failed: {res.text}"

        res = client.patch(f"/api/admin/users/{user_id}",
                           json={"allowed_studies": ["BioBank"]},
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200, f"Study scope update failed: {res.text}"
        print("[OK] Admin successfully restricted user to 'BioBank' study.")

        print("\n--- 4. Re-Login as Restricted User & Verify Token/Profile ---")
        res = client.post("/api/auth/login", json={"email": restricted_email, "password": password})
        assert res.status_code == 200
        user_token = res.json()["token"]
        assert res.json()["user"]["allowed_studies"] == ["BioBank"]
        print("[OK] Restricted user profile correctly shows allowed_studies=['BioBank'].")

        print("\n--- 5. Perform Search as Restricted User ---")
        res = client.get("/api/search", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200, f"Search failed: {res.text}"
        search_data = res.json()
        results = search_data.get("results", [])
        print(f"Returned {len(results)} samples for BioBank-scoped user.")
        
        # Assert all returned samples have Study == 'BioBank'
        non_biobank = [r for r in results if str(r.get("metadata", {}).get("Study", "")).strip().lower() != "biobank"]
        assert len(non_biobank) == 0, f"Found {len(non_biobank)} unauthorized study records in search results!"
        print("[OK] 100% of search results strictly belong to 'BioBank'.")

        print("\n--- 6. Verify Scoped Stats API ---")
        res = client.get("/api/stats", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200
        stats = res.json()
        print(f"Scoped Stats -> Samples: {stats['samples']}, Studies: {stats['study_list']}")
        assert set(s.lower() for s in stats["study_list"]) == {"biobank"}
        print("[OK] Scoped /api/stats dynamically returns data strictly for 'BioBank'.")

        print("\n--- 7. Admin Expands Access to ['BioBank', 'Biopharma'] ---")
        res = client.patch(f"/api/admin/users/{user_id}",
                           json={"allowed_studies": ["BioBank", "Biopharma"]},
                           headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

        res = client.get("/api/stats", headers={"Authorization": f"Bearer {user_token}"})
        assert res.status_code == 200
        stats = res.json()
        print(f"Updated Stats -> Studies: {stats['study_list']}")
        assert set(s.lower() for s in stats["study_list"]) == {"biobank", "biopharma"}
        print("[OK] Expanded study access permissions successfully verified!")


        print("\n=== STUDY-LEVEL ACCESS CONTROL (RBAC) TEST PASSED SUCCESSFULLY! ===\n")

if __name__ == "__main__":
    test_study_access_control()
