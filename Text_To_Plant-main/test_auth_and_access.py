"""
test_auth_and_access.py
Comprehensive 12-Scenario Automated Verification Suite for Department-Based Authentication,
Database-backed Account Lifecycle, Paid Department Activation, Subscription Validation, and API Protection.
"""

import sys
import os
import json
import datetime

# Ensure project directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app
import db
from init_db import seed_database
from auth import hash_password, verify_password

def run_all_acceptance_tests():
    print("==========================================================")
    print("RUNNING 12-SCENARIO DEPARTMENT AUTH & SUBSCRIPTION SUITE")
    print("==========================================================")

    # 1. Initialize and Seed Database
    seed_database()
    client = app.test_client()
    
    passed_tests = 0
    total_tests = 12

    # ----------------------------------------------------
    # TEST 1: Department Login with Valid ACTIVE Credentials
    # ----------------------------------------------------
    try:
        res = client.post("/login", data={
            "department_code": "BOTANY001",
            "password": "Botany@Password123"
        }, follow_redirects=False)

        if res.status_code == 302 and "/dashboard" in res.headers.get("Location", ""):
            print("[PASS] Test 1 — Valid ACTIVE Department Login -> Succeeded & Redirected to /dashboard")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 1 — Expected 302 to /dashboard, got {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Test 1 -> {e}")

    # ----------------------------------------------------
    # TEST 2: Wrong Password Rejection
    # ----------------------------------------------------
    try:
        res = client.post("/login", data={
            "department_code": "BOTANY001",
            "password": "IncorrectPassword123!"
        }, follow_redirects=True)

        if "Invalid Department ID or Password" in res.get_data(as_text=True):
            print("[PASS] Test 2 — Wrong Password -> Correctly Rejected with Authentication Error")
            passed_tests += 1
        else:
            print("[FAIL] Test 2 — Wrong password did not trigger rejection message")
    except Exception as e:
        print(f"[ERROR] Test 2 -> {e}")

    # ----------------------------------------------------
    # TEST 3: Pending Department Access Blocked
    # ----------------------------------------------------
    try:
        res = client.post("/login", data={
            "department_code": "AGRI001",
            "password": "Agri@Password123"
        }, follow_redirects=True)

        page_text = res.get_data(as_text=True)
        if "awaiting activation" in page_text.lower():
            print("[PASS] Test 3 — Pending Department -> Access Denied ('awaiting activation')")
            passed_tests += 1
        else:
            print("[FAIL] Test 3 — Expected pending activation message")
    except Exception as e:
        print(f"[ERROR] Test 3 -> {e}")

    # ----------------------------------------------------
    # TEST 4: Suspended Department Access Blocked
    # ----------------------------------------------------
    try:
        res = client.post("/login", data={
            "department_code": "BIOTECH001",
            "password": "Biotech@Password123"
        }, follow_redirects=True)

        page_text = res.get_data(as_text=True)
        if "suspended" in page_text.lower():
            print("[PASS] Test 4 — Suspended Department -> Access Denied ('access has been suspended')")
            passed_tests += 1
        else:
            print("[FAIL] Test 4 — Expected suspended message")
    except Exception as e:
        print(f"[ERROR] Test 4 -> {e}")

    # ----------------------------------------------------
    # TEST 5: Expired Department Access Blocked
    # ----------------------------------------------------
    try:
        res = client.post("/login", data={
            "department_code": "PHARMA001",
            "password": "Pharma@Password123"
        }, follow_redirects=True)

        page_text = res.get_data(as_text=True)
        if "expired" in page_text.lower():
            print("[PASS] Test 5 — Expired Department -> Access Denied ('subscription has expired')")
            passed_tests += 1
        else:
            print("[FAIL] Test 5 — Expected expired subscription message")
    except Exception as e:
        print(f"[ERROR] Test 5 -> {e}")

    # ----------------------------------------------------
    # TEST 6: Active Department Plant Identification
    # ----------------------------------------------------
    try:
        # Authenticate session as BOTANY001
        with client.session_transaction() as sess:
            botany_dept = db.get_department_by_code("BOTANY001")
            sess["department_id"] = botany_dept["id"]
            sess["department_code"] = botany_dept["department_code"]
            sess["department_name"] = botany_dept["department_name"]

        res = client.post("/api/predict", json={
            "description": "A small tree with bright red flowers, glossy leaves, and round red fruit with juicy edible seeds inside like Pomegranate."
        })

        data = res.get_json()
        if res.status_code == 200 and data.get("is_plant") is True and len(data.get("results", [])) > 0:
            pred_name = data["results"][0].get("Common_Name")
            print(f"[PASS] Test 6 — Active Department Identification -> Success (Identified: '{pred_name}')")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 6 — Expected active identification, got {res.status_code}: {data}")
    except Exception as e:
        print(f"[ERROR] Test 6 -> {e}")

    # ----------------------------------------------------
    # TEST 7: Unauthenticated API Request Blocked (401)
    # ----------------------------------------------------
    try:
        unauth_client = app.test_client()
        res = unauth_client.post("/api/predict", json={
            "description": "Aloe vera succulent plant with thick fleshy leaves"
        })

        if res.status_code == 401:
            print("[PASS] Test 7 — Unauthenticated API Request -> Correctly Blocked (HTTP 401 Unauthorized)")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 7 — Expected HTTP 401, got {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Test 7 -> {e}")

    # ----------------------------------------------------
    # TEST 8: New Department Workflow (Initially PENDING)
    # ----------------------------------------------------
    try:
        admin_client = app.test_client()
        with admin_client.session_transaction() as sess:
            admin_acc = db.get_admin_by_username("admin")
            sess["admin_id"] = admin_acc["id"]
            sess["admin_username"] = admin_acc["username"]

        # Admin creates new department ENV001
        res = admin_client.post("/admin/departments/create", data={
            "department_name": "Environmental Science Department",
            "department_code": "ENV001",
            "institution_name": "Institute of Ecology",
            "contact_email": "env@ecology.org",
            "subscription_plan": "Annual Department License",
            "password": "Env@Password123"
        }, follow_redirects=True)

        new_dept = db.get_department_by_code("ENV001")
        if new_dept and new_dept["status"] == "PENDING" and new_dept["payment_status"] == "PENDING":
            print(f"[PASS] Test 8 — New Department Workflow -> Created as PENDING with Invoice Generated")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 8 — Department not created in PENDING status: {new_dept}")
    except Exception as e:
        print(f"[ERROR] Test 8 -> {e}")

    # ----------------------------------------------------
    # TEST 9: Payment Verification & Activation
    # ----------------------------------------------------
    try:
        # Find payment for ENV001
        env_dept = db.get_department_by_code("ENV001")
        payments = db.get_payments_for_department(env_dept["id"])
        if payments:
            pay_ref = payments[0]["payment_reference"]
            # Verify payment
            res = client.post("/api/payment/verify", data={
                "payment_reference": pay_ref,
                "gateway_ref": "TXN_ENV_SUCCESS_123"
            })
            
            env_updated = db.get_department_by_code("ENV001")
            if env_updated["status"] == "ACTIVE" and env_updated["payment_status"] == "PAID":
                print(f"[PASS] Test 9 — Payment Verification -> Department Activated & Payment Marked PAID")
                passed_tests += 1
            else:
                print(f"[FAIL] Test 9 — Status not updated to ACTIVE: {env_updated}")
        else:
            print("[FAIL] Test 9 — No pending payment found for ENV001")
    except Exception as e:
        print(f"[ERROR] Test 9 -> {e}")

    # ----------------------------------------------------
    # TEST 10: Subscription Expiration Dynamic Enforcement
    # ----------------------------------------------------
    try:
        # Test API call with expired department PHARMA001
        exp_client = app.test_client()
        with exp_client.session_transaction() as sess:
            pharma_dept = db.get_department_by_code("PHARMA001")
            sess["department_id"] = pharma_dept["id"]
            sess["department_code"] = pharma_dept["department_code"]

        res = exp_client.post("/api/predict", json={
            "description": "Turmeric perennial herb"
        })

        if res.status_code == 403:
            print("[PASS] Test 10 — Subscription Expiration -> API Access Blocked (HTTP 403 Forbidden)")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 10 — Expected HTTP 403 for expired department, got {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Test 10 -> {e}")

    # ----------------------------------------------------
    # TEST 11: Admin Management Operations
    # ----------------------------------------------------
    try:
        admin_client = app.test_client()
        with admin_client.session_transaction() as sess:
            admin_acc = db.get_admin_by_username("admin")
            sess["admin_id"] = admin_acc["id"]
            sess["admin_username"] = admin_acc["username"]

        # 1. Suspend ENV001
        env_dept = db.get_department_by_code("ENV001")
        admin_client.post(f"/admin/departments/{env_dept['id']}/status", data={"status": "SUSPENDED"})
        env_after_suspend = db.get_department_by_code("ENV001")

        # 2. Reset password
        admin_client.post(f"/admin/departments/{env_dept['id']}/reset-password", data={"new_password": "NewEnv@Pass2026!"})
        env_after_pwd = db.get_department_by_code("ENV001")
        pwd_verified = verify_password("NewEnv@Pass2026!", env_after_pwd["password_hash"])

        # 3. Renew subscription (+12 months)
        admin_client.post(f"/admin/departments/{env_dept['id']}/renew", data={"duration_months": "12"})
        env_after_renew = db.get_department_by_code("ENV001")

        if env_after_suspend["status"] == "SUSPENDED" and pwd_verified and env_after_renew["status"] == "ACTIVE":
            print("[PASS] Test 11 — Admin Capabilities -> Suspend, Password Reset & Renewal Verified")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 11 — Admin operations failed")
    except Exception as e:
        print(f"[ERROR] Test 11 -> {e}")

    # ----------------------------------------------------
    # TEST 12: Department Isolation & Audit Logging
    # ----------------------------------------------------
    try:
        # Check audit logs are recorded and department cannot access admin dashboard
        dept_client = app.test_client()
        with dept_client.session_transaction() as sess:
            botany_dept = db.get_department_by_code("BOTANY001")
            sess["department_id"] = botany_dept["id"]
            sess["department_code"] = botany_dept["department_code"]

        # Department tries to access /admin/dashboard
        admin_access_res = dept_client.get("/admin/dashboard", follow_redirects=False)
        
        # Verify recent audit logs exist
        logs = db.get_recent_audit_logs(limit=20)
        has_audit_entries = len(logs) > 0

        if admin_access_res.status_code == 302 and "/admin/login" in admin_access_res.headers.get("Location", "") and has_audit_entries:
            print("[PASS] Test 12 — Department Isolation -> Admin Area Protected & Audit Logs Verified")
            passed_tests += 1
        else:
            print(f"[FAIL] Test 12 — Department isolation failed or no audit logs found")
    except Exception as e:
        print(f"[ERROR] Test 12 -> {e}")

    print("==========================================================")
    print(f"ACCEPTANCE SUITE RESULTS: {passed_tests} / {total_tests} PASSED ({passed_tests/total_tests*100:.1f}%)")
    print("==========================================================")
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_all_acceptance_tests()
    sys.exit(0 if success else 1)
