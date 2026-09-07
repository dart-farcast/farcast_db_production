"""
FarCast DB v2 — Comprehensive Security, RBAC, IDOR, and Failure Test Suite
Validates authentication hardening, password policy, token revocation,
study-level RBAC, object-level authorization (IDOR), SQL injection resilience,
rate limiting, and readiness probes.
"""
import sys
import time
import requests
from fastapi.testclient import TestClient

from app import app
from database.auth_db import get_db_connection, hash_password, validate_password_strength
from api.cache import cache, reload_cache

def run_security_tests():
    print("\n" + "=" * 70)
    print("  FARCAST DB v2 — AUTOMATED PRODUCTION SECURITY & RESILIENCE TEST SUITE")
    print("=" * 70 + "\n")

    with TestClient(app) as client:
        passed_count = 0
        total_count = 0


    def assert_test(condition: bool, description: str):
        nonlocal passed_count, total_count
        total_count += 1
        if condition:
            passed_count += 1
            print(f"  [PASS] {description}")
        else:
            print(f"  [FAIL] {description}")
            assert False, f"Test failed: {description}"

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Password Policy & Complexity Validation
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 1. Password Policy & Complexity Validation ---")
    
    ok, _ = validate_password_strength("short1A")
    assert_test(not ok, "Rejects password under 8 characters")

    ok, _ = validate_password_strength("nouppercase123")
    assert_test(not ok, "Rejects password without uppercase letters")

    ok, _ = validate_password_strength("NOLOWERCASE123")
    assert_test(not ok, "Rejects password without lowercase letters")

    ok, _ = validate_password_strength("NoDigitsHere!")
    assert_test(not ok, "Rejects password without digits")

    ok, _ = validate_password_strength("password123")
    assert_test(not ok, "Rejects common trivial password 'password123'")

    ok, _ = validate_password_strength("FarCastSecure#2026")
    assert_test(ok, "Accepts strong compliant password ('FarCastSecure#2026')")

    # Registration with weak password
    res = client.post("/api/auth/register", json={
        "email": "weakpass@farcastbio.com",
        "password": "123",
        "full_name": "Weak Pass User"
    })
    assert_test(res.status_code == 400 or res.status_code == 422, "API blocks registration with weak password")

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Authentication, Token Issuance & Revocation (Logout)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 2. Authentication, Token Issuance & Revocation (Logout) ---")

    # Admin Login
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@farcastbio.com",
        "password": "admin123"
    })
    assert_test(admin_login.status_code == 200, "Admin login successful")
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers=admin_headers)
    assert_test(me_res.status_code == 200 and me_res.json()["user"]["role"] == "admin", 
                "Decoded token payload identifies valid admin user")

    # Register dynamic test user
    test_user_email = f"sec_user_{int(time.time())}@farcastbio.com"
    reg_res = client.post("/api/auth/register", json={
        "email": test_user_email,
        "password": "StrongPassword!2026",
        "full_name": "Security Test User"
    })
    assert_test(reg_res.status_code == 200, "Compliant user registered and auto-whitelisted")
    user_token = reg_res.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Verify user can access database routes
    stats_res = client.get("/api/stats", headers=user_headers)
    assert_test(stats_res.status_code == 200, "Active token permits database access")

    # Test Logout & Session Revocation
    logout_res = client.post("/api/auth/logout", headers=user_headers)
    assert_test(logout_res.status_code == 200, "Logout endpoint revokes JWT session")

    # Attempt to reuse revoked token
    revoked_stats_res = client.get("/api/stats", headers=user_headers)
    assert_test(revoked_stats_res.status_code == 401, "Revoked token is strictly rejected (HTTP 401)")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. RBAC & Administrative Route Protection
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 3. Role-Based Access Control (RBAC) Protection ---")

    # Re-login as standard user
    relogin = client.post("/api/auth/login", json={
        "email": test_user_email,
        "password": "StrongPassword!2026"
    })
    user_token = relogin.json()["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}
    user_id = relogin.json()["user"]["id"]

    # Non-admin user attempts admin endpoints
    unauth_users = client.get("/api/admin/users", headers=user_headers)
    assert_test(unauth_users.status_code == 403, "Standard user blocked from /api/admin/users (HTTP 403)")

    unauth_audit = client.get("/api/admin/audit_logs", headers=user_headers)
    assert_test(unauth_audit.status_code == 403, "Standard user blocked from /api/admin/audit_logs (HTTP 403)")

    unauth_upload = client.post("/api/upload", data={"table": "malicious"}, headers=user_headers)
    assert_test(unauth_upload.status_code == 403, "Standard user blocked from /api/upload (HTTP 403)")

    # ──────────────────────────────────────────────────────────────────────────
    # 4. Study-Level Isolation & IDOR Protection
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 4. Study-Level Isolation & IDOR/BOLA Protection ---")

    # Admin restricts test user to 'BioBank' study only
    scope_res = client.patch(f"/api/admin/users/{user_id}", json={
        "allowed_studies": ["BioBank"]
    }, headers=admin_headers)
    assert_test(scope_res.status_code == 200, "Admin restricts test user study scope to ['BioBank']")

    # Re-login to get updated study scope
    relogin_scoped = client.post("/api/auth/login", json={
        "email": test_user_email,
        "password": "StrongPassword!2026"
    })
    scoped_token = relogin_scoped.json()["token"]
    scoped_headers = {"Authorization": f"Bearer {scoped_token}"}

    # Perform search as restricted user
    search_res = client.get("/api/search", headers=scoped_headers)
    results = search_res.json().get("results", [])
    assert_test(len(results) > 0, f"Scoped user retrieved {len(results)} samples")
    all_biobank = all(r["metadata"].get("Study", "").lower() == "biobank" for r in results)
    assert_test(all_biobank, "100% of search results belong strictly to 'BioBank'")

    # Autocomplete study scoping
    auto_study = client.get("/api/autocomplete?field=study", headers=scoped_headers)
    assert_test(auto_study.json() == ["BioBank"], "Autocomplete field=study strictly returns allowed study only")

    # IDOR Test on /api/sample_assays
    # Find a sample that belongs to another study (e.g. 'Biopharma' or 'Internal R&D')
    other_sample = None
    for sid, m in cache.meta_idx.items():
        if str(m.get("Study", "")).strip().lower() != "biobank":
            other_sample = sid
            break

    if other_sample:
        idor_sample_res = client.get(f"/api/sample_assays?sample_id={other_sample}", headers=scoped_headers)
        assert_test(idor_sample_res.status_code == 403, 
                    f"IDOR Blocked: Restricted user denied assay data for unauthorized sample '{other_sample}' (HTTP 403)")

    # IDOR Test on /api/cohort_assays
    if other_sample:
        biobank_sample = results[0]["metadata"]["Sample_ID"]
        cohort_res = client.post("/api/cohort_assays", json={
            "sample_ids": [biobank_sample, other_sample]
        }, headers=scoped_headers)
        cohort_data = cohort_res.json()
        # Verify unauthorized sample rows are filtered out
        for aname, adata in cohort_data.items():
            sids_in_rows = {r.get("Sample_ID") for r in adata.get("rows", [])}
            assert_test(other_sample not in sids_in_rows, 
                        f"IDOR Blocked in cohort_assays: '{other_sample}' stripped from {aname} assay results")

    # ──────────────────────────────────────────────────────────────────────────
    # 5. SQL Injection & Input Validation Hardening
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 5. SQL Injection & Input Validation Resilience ---")

    sqli_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT NULL, NULL, NULL, NULL --",
        "1' OR '1' = '1"
    ]

    for sqli in sqli_payloads:
        sqli_res = client.get(f"/api/search?drug={sqli}&indication={sqli}", headers=admin_headers)
        assert_test(sqli_res.status_code == 200, f"Search safely handles SQL injection payload: {sqli}")
        assert_test(sqli_res.json()["total"] == 0, "SQL injection yields 0 matched samples (no data leak)")

    # Oversized parameter check
    huge_param = "A" * 1000
    huge_res = client.get(f"/api/search?sample={huge_param}", headers=admin_headers)
    assert_test(huge_res.status_code == 422 or huge_res.status_code == 200, "Oversized parameter handled gracefully")

    # ──────────────────────────────────────────────────────────────────────────
    # 6. Health & Readiness Probes
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 6. Health & Readiness Probes ---")

    live_res = client.get("/health/live")
    assert_test(live_res.status_code == 200 and live_res.json()["status"] == "alive", 
                "GET /health/live probe returns 200 OK")

    ready_res = client.get("/health/ready")
    assert_test(ready_res.status_code == 200 and ready_res.json()["status"] == "ready", 
                "GET /health/ready probe returns 200 OK with cache and DB validated")
    assert_test(ready_res.json()["samples_loaded"] > 0, "Readiness probe confirms loaded sample universe")

    # ──────────────────────────────────────────────────────────────────────────
    # 7. Security Headers Verification
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 7. OWASP Security Headers Verification ---")

    headers_res = client.get("/health/live")
    h = headers_res.headers
    assert_test(h.get("X-Content-Type-Options") == "nosniff", "Header X-Content-Type-Options: nosniff present")
    assert_test(h.get("X-Frame-Options") == "DENY", "Header X-Frame-Options: DENY present")
    assert_test(h.get("X-XSS-Protection") == "1; mode=block", "Header X-XSS-Protection present")
    assert_test("X-Request-ID" in h, "Header X-Request-ID present for request correlation")

    # ──────────────────────────────────────────────────────────────────────────
    # 8. Rate Limiting Protection
    # ──────────────────────────────────────────────────────────────────────────
    print("\n--- 8. Rate Limiting Verification ---")
    
    rate_limited = False
    for i in range(25):
        r = client.post("/api/auth/login", json={"email": "ratelimit@test.com", "password": "wrong"})
        if r.status_code == 429:
            rate_limited = True
            break

    assert_test(rate_limited, "Rate limiter triggers HTTP 429 Too Many Requests after burst login attempts")

    # ──────────────────────────────────────────────────────────────────────────
    # Final Summary
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print(f"  ALL {passed_count}/{total_count} SECURITY & RESILIENCE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")
    return True

if __name__ == "__main__":
    success = run_security_tests()
    if not success:
        sys.exit(1)
