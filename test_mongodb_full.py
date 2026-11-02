"""
test_mongodb_full.py
Comprehensive test suite verifying that all db.py functions execute correctly
with MongoDB backend (collections, indexes, queries, mutations, serialization).
"""

import os
os.environ["MONGO_URI"] = "mongomock://localhost/text_to_plant"

import db
from auth import hash_password

def test_mongodb_operations():
    print("==========================================================")
    print("MONGODB BACKEND VERIFICATION TEST SUITE")
    print("==========================================================")

    # 1. Connection check
    assert db.is_mongo_active(), "MongoDB should be active"
    info = db.get_database_info()
    print(f"[OK] Database engine detected: {info['engine']}")
    assert info["engine"] == "MongoDB"

    # 2. Schema initialization
    db.init_database_tables()
    print("[OK] Schema & unique indexes initialized")

    # 3. Admins
    admin_id = db.create_admin("superadmin", hash_password("SuperSecure#2026"))
    assert admin_id is not None
    admin = db.get_admin_by_username("superadmin")
    assert admin is not None
    assert admin["username"] == "superadmin"
    db.update_admin_last_login(admin["id"])
    print(f"[OK] Admin created and verified: ID {admin['id']}")

    # 4. Subscription Plans
    plan_id = db.create_subscription_plan("Campus Unlimited", 12, 10000.0, "INR")
    plans = db.get_all_subscription_plans()
    assert any(p["name"] == "Campus Unlimited" for p in plans)
    print(f"[OK] Subscription plan created: ID {plan_id}, total plans: {len(plans)}")

    # 5. Departments
    dept_id = db.create_department(
        department_name="Department of Horticulture",
        department_code="HORT001",
        institution_name="State Agricultural College",
        contact_email="hort@agri.edu",
        password_hash=hash_password("Hort@2026Secure"),
        subscription_plan="Campus Unlimited"
    )
    assert dept_id is not None
    dept = db.get_department_by_code("HORT001")
    assert dept is not None
    assert dept["department_code"] == "HORT001"
    assert dept["status"] == "PENDING"
    
    # Test date slicing compatibility (which Jinja templates do)
    db.activate_department_subscription(dept_id, duration_months=12)
    dept_active = db.get_department_by_id(dept_id)
    assert dept_active["status"] == "ACTIVE"
    assert isinstance(dept_active["subscription_end"], str)
    date_slice = dept_active["subscription_end"][:10]
    print(f"[OK] Department activated: status={dept_active['status']}, valid_until={date_slice}")

    # 6. Payments
    pay_id = db.create_payment_record(
        department_id=dept_id,
        payment_reference="PAY-HORT001-TEST",
        amount=10000.0,
        currency="INR",
        duration_months=12,
        notes="Automated test payment"
    )
    assert pay_id is not None
    pay = db.get_payment_by_reference("PAY-HORT001-TEST")
    assert pay["payment_status"] == "PENDING"

    verify_res = db.mark_payment_verified("PAY-HORT001-TEST", gateway_reference="GW_TEST_999", duration_months=12)
    assert verify_res is True
    pay_updated = db.get_payment_by_reference("PAY-HORT001-TEST")
    assert pay_updated["payment_status"] == "PAID"
    all_dept_payments = db.get_payments_for_department(dept_id)
    assert len(all_dept_payments) >= 1
    print(f"[OK] Payment verified: Ref={pay_updated['payment_reference']}, Status={pay_updated['payment_status']}")

    # 7. Audit Logging
    log_id = db.record_audit_log(
        action="Department HORT001 registered and paid",
        department_id=dept_id,
        department_code="HORT001",
        ip_address="127.0.0.1"
    )
    logs = db.get_recent_audit_logs(limit=10)
    assert any(l["id"] == log_id for l in logs)
    print(f"[OK] Audit log recorded and retrieved: Total recent logs={len(logs)}")

    # 8. Dashboard Statistics
    stats = db.get_admin_dashboard_stats()
    assert stats["total_departments"] >= 1
    assert stats["active_departments"] >= 1
    assert stats["total_payments"] >= 1
    assert stats["total_revenue"] >= 10000.0
    print(f"[OK] Dashboard Stats: {stats}")

    print("==========================================================")
    print("ALL MONGODB BACKEND TESTS PASSED (100% OPERATIONAL)")
    print("==========================================================")

if __name__ == "__main__":
    test_mongodb_operations()
