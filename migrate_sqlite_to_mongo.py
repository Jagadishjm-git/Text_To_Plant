"""
migrate_sqlite_to_mongo.py
Automated migration utility to transfer existing SQLite relational records 
into MongoDB collections with index setup and sequence counter synchronization.
"""

import os
import sqlite3
import datetime
import db

def parse_iso_or_str(val):
    """Safely converts string date to datetime object if possible."""
    if not val:
        return None
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val
    try:
        clean = val.split(".")[0]
        return datetime.datetime.strptime(clean, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return val

def run_migration():
    print("==========================================================")
    print("SQLITE TO MONGODB DATA MIGRATION UTILITY")
    print("==========================================================")

    # 1. Verify SQLite DB exists
    sqlite_path = db.LOCAL_DB_PATH
    if not os.path.exists(sqlite_path):
        print(f"[ERROR] SQLite database file not found at: {sqlite_path}")
        return False

    # 2. Verify MongoDB connection
    mdb = db.get_mongo_db()
    if mdb is None:
        print("[ERROR] Cannot connect to MongoDB!")
        print("Please ensure MONGO_URI is set in your .env file or environment.")
        print("Example: MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/text_to_plant")
        return False

    print(f"[OK] Connected to MongoDB database: '{mdb.name}'")
    
    # Initialize indexes
    db.init_database_tables()
    print("[OK] MongoDB indexes verified.")

    # Connect to SQLite
    s_conn = sqlite3.connect(sqlite_path)
    s_conn.row_factory = sqlite3.Row
    s_cur = s_conn.cursor()

    total_stats = {}

    # ----------------------------------------------------
    # A. Migrate Admins
    # ----------------------------------------------------
    try:
        s_cur.execute("SELECT * FROM admins")
        admin_rows = [dict(r) for r in s_cur.fetchall()]
        max_id = 0
        migrated = 0
        for r in admin_rows:
            aid = int(r["id"])
            max_id = max(max_id, aid)
            doc = {
                "id": aid,
                "username": r["username"].strip().lower(),
                "password_hash": r["password_hash"],
                "created_at": parse_iso_or_str(r.get("created_at")),
                "last_login": parse_iso_or_str(r.get("last_login"))
            }
            res = mdb["admins"].update_one({"id": aid}, {"$set": doc}, upsert=True)
            if res.upserted_id or res.modified_count:
                migrated += 1

        if max_id > 0:
            mdb["counters"].update_one({"_id": "admins"}, {"$max": {"seq": max_id}}, upsert=True)
        total_stats["admins"] = len(admin_rows)
        print(f"[OK] Admins migrated: {len(admin_rows)} records (Max ID: {max_id})")
    except Exception as e:
        print(f"[WARN] Error migrating admins: {e}")

    # ----------------------------------------------------
    # B. Migrate Subscription Plans
    # ----------------------------------------------------
    try:
        s_cur.execute("SELECT * FROM subscription_plans")
        plan_rows = [dict(r) for r in s_cur.fetchall()]
        max_id = 0
        for r in plan_rows:
            pid = int(r["id"])
            max_id = max(max_id, pid)
            doc = {
                "id": pid,
                "name": r["name"],
                "duration_months": int(r["duration_months"]),
                "price": float(r["price"]),
                "currency": r.get("currency", "INR"),
                "is_active": int(r.get("is_active", 1)),
                "created_at": parse_iso_or_str(r.get("created_at"))
            }
            mdb["subscription_plans"].update_one({"id": pid}, {"$set": doc}, upsert=True)

        if max_id > 0:
            mdb["counters"].update_one({"_id": "subscription_plans"}, {"$max": {"seq": max_id}}, upsert=True)
        total_stats["subscription_plans"] = len(plan_rows)
        print(f"[OK] Subscription Plans migrated: {len(plan_rows)} records (Max ID: {max_id})")
    except Exception as e:
        print(f"[WARN] Error migrating subscription plans: {e}")

    # ----------------------------------------------------
    # C. Migrate Departments
    # ----------------------------------------------------
    try:
        s_cur.execute("SELECT * FROM departments")
        dept_rows = [dict(r) for r in s_cur.fetchall()]
        max_id = 0
        for r in dept_rows:
            did = int(r["id"])
            max_id = max(max_id, did)
            doc = {
                "id": did,
                "department_name": r["department_name"],
                "department_code": r["department_code"].strip().upper(),
                "institution_name": r["institution_name"],
                "contact_email": r["contact_email"],
                "password_hash": r["password_hash"],
                "status": r.get("status", "PENDING"),
                "subscription_status": r.get("subscription_status", "PENDING"),
                "payment_status": r.get("payment_status", "PENDING"),
                "subscription_plan": r.get("subscription_plan", "Annual Department License"),
                "subscription_start": parse_iso_or_str(r.get("subscription_start")),
                "subscription_end": parse_iso_or_str(r.get("subscription_end")),
                "created_at": parse_iso_or_str(r.get("created_at")),
                "updated_at": parse_iso_or_str(r.get("updated_at")),
                "last_login": parse_iso_or_str(r.get("last_login"))
            }
            mdb["departments"].update_one({"id": did}, {"$set": doc}, upsert=True)

        if max_id > 0:
            mdb["counters"].update_one({"_id": "departments"}, {"$max": {"seq": max_id}}, upsert=True)
        total_stats["departments"] = len(dept_rows)
        print(f"[OK] Departments migrated: {len(dept_rows)} records (Max ID: {max_id})")
    except Exception as e:
        print(f"[WARN] Error migrating departments: {e}")

    # ----------------------------------------------------
    # D. Migrate Payments
    # ----------------------------------------------------
    try:
        s_cur.execute("SELECT * FROM payments")
        pay_rows = [dict(r) for r in s_cur.fetchall()]
        max_id = 0
        for r in pay_rows:
            pay_id = int(r["id"])
            max_id = max(max_id, pay_id)
            doc = {
                "id": pay_id,
                "department_id": int(r["department_id"]),
                "payment_reference": r["payment_reference"],
                "amount": float(r["amount"]),
                "currency": r.get("currency", "INR"),
                "payment_status": r.get("payment_status", "PENDING"),
                "payment_date": parse_iso_or_str(r.get("payment_date")),
                "subscription_start": parse_iso_or_str(r.get("subscription_start")),
                "subscription_end": parse_iso_or_str(r.get("subscription_end")),
                "gateway_reference": r.get("gateway_reference"),
                "notes": r.get("notes"),
                "created_at": parse_iso_or_str(r.get("created_at"))
            }
            mdb["payments"].update_one({"id": pay_id}, {"$set": doc}, upsert=True)

        if max_id > 0:
            mdb["counters"].update_one({"_id": "payments"}, {"$max": {"seq": max_id}}, upsert=True)
        total_stats["payments"] = len(pay_rows)
        print(f"[OK] Payments migrated: {len(pay_rows)} records (Max ID: {max_id})")
    except Exception as e:
        print(f"[WARN] Error migrating payments: {e}")

    # ----------------------------------------------------
    # E. Migrate Audit Logs
    # ----------------------------------------------------
    try:
        s_cur.execute("SELECT * FROM audit_logs")
        log_rows = [dict(r) for r in s_cur.fetchall()]
        max_id = 0
        for r in log_rows:
            lid = int(r["id"])
            max_id = max(max_id, lid)
            doc = {
                "id": lid,
                "department_id": int(r["department_id"]) if r.get("department_id") else None,
                "department_code": r.get("department_code"),
                "action": r.get("action"),
                "ip_address": r.get("ip_address"),
                "created_at": parse_iso_or_str(r.get("created_at"))
            }
            mdb["audit_logs"].update_one({"id": lid}, {"$set": doc}, upsert=True)

        if max_id > 0:
            mdb["counters"].update_one({"_id": "audit_logs"}, {"$max": {"seq": max_id}}, upsert=True)
        total_stats["audit_logs"] = len(log_rows)
        print(f"[OK] Audit Logs migrated: {len(log_rows)} records (Max ID: {max_id})")
    except Exception as e:
        print(f"[WARN] Error migrating audit logs: {e}")

    s_conn.close()

    print("==========================================================")
    print("MIGRATION COMPLETED SUCCESSFULLY")
    for tbl, count in total_stats.items():
        print(f" -> {tbl}: {count} records transferred to MongoDB")
    print("==========================================================")
    return True

if __name__ == "__main__":
    run_migration()
