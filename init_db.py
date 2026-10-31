"""
init_db.py
Database Initialization & Seeding Script for Department-Based Plant Identification Portal.
Creates tables, default admin, standard subscription plans, and standard test departments.
"""

import os
import datetime
import db
from auth import hash_password

def seed_database():
    print("==========================================================")
    print("INITIALIZING DATABASE & SEEDING INITIAL DATA")
    print("==========================================================")

    # 1. Initialize Tables
    db.init_database_tables()
    print("[OK] Database tables verified and created successfully.")

    # 2. Seed Default Administrator Account
    admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
    admin_pass = os.environ.get("ADMIN_PASSWORD", "Admin@BotanicalPortal2026#Secure").strip()
    
    existing_admin = db.get_admin_by_username(admin_user)
    if not existing_admin:
        admin_hash = hash_password(admin_pass)
        db.create_admin(admin_user, admin_hash)
        print(f"[OK] Default Administrator account created -> Username: '{admin_user}', Password: '{admin_pass}'")
    else:
        print(f"[OK] Administrator account '{admin_user}' already exists.")

    # 3. Seed Standard Subscription Plans
    existing_plans = db.get_all_subscription_plans()
    if not existing_plans:
        standard_plans = [
            ("Monthly Department Pass", 1, 1000.0, "INR"),
            ("Quarterly Department License", 3, 2500.0, "INR"),
            ("Semi-Annual Department License", 6, 4000.0, "INR"),
            ("Annual Department License", 12, 5000.0, "INR")
        ]
        for name, months, price, curr in standard_plans:
            db.create_subscription_plan(name, months, price, curr)
        print("[OK] Standard institutional subscription plans initialized.")
    else:
        print(f"[OK] {len(existing_plans)} subscription plans active.")

    # 4. Seed Standard Test Departments
    # Department 1: ACTIVE Department (Botany Department - BOTANY001)
    dept_botany = db.get_department_by_code("BOTANY001")
    if not dept_botany:
        dept_id = db.create_department(
            department_name="Botany Department",
            department_code="BOTANY001",
            institution_name="National Botanical Research Institute",
            contact_email="botany@nbri.res.in",
            password_hash=hash_password("Botany#Secure2026Pass"),
            subscription_plan="Annual Department License"
        )
        # Activate with 12-month subscription
        db.activate_department_subscription(dept_id, duration_months=12)
        # Create payment record
        pay_id = db.create_payment_record(
            department_id=dept_id,
            payment_reference="PAY-BOTANY001-INIT",
            amount=5000.0,
            currency="INR",
            duration_months=12,
            notes="Initial Annual License Payment (Seed)"
        )
        db.mark_payment_verified("PAY-BOTANY001-INIT", gateway_reference="SEED_GATEWAY_SUCCESS", duration_months=12)
        db.record_audit_log("BOTANY001 account created and activated for 12 months", department_id=dept_id, department_code="BOTANY001")
        print("[OK] Test Department Created: BOTANY001 (Status: ACTIVE, Expiry: 12 months)")

    # Department 2: PENDING Department (Agriculture Department - AGRI001)
    dept_agri = db.get_department_by_code("AGRI001")
    if not dept_agri:
        agri_id = db.create_department(
            department_name="Agriculture Department",
            department_code="AGRI001",
            institution_name="State Agricultural University",
            contact_email="agri@state-agri.edu",
            password_hash=hash_password("Agri@Password123"),
            subscription_plan="Annual Department License"
        )
        db.create_payment_record(
            department_id=agri_id,
            payment_reference="PAY-AGRI001-PENDING",
            amount=5000.0,
            currency="INR",
            duration_months=12,
            notes="Pending payment invoice"
        )
        db.record_audit_log("AGRI001 account created (Status: PENDING payment)", department_id=agri_id, department_code="AGRI001")
        print("[OK] Test Department Created: AGRI001 (Status: PENDING activation)")

    # Department 3: SUSPENDED Department (Biotechnology Department - BIOTECH001)
    dept_biotech = db.get_department_by_code("BIOTECH001")
    if not dept_biotech:
        bio_id = db.create_department(
            department_name="Biotechnology Department",
            department_code="BIOTECH001",
            institution_name="Central University of Science",
            contact_email="biotech@central-univ.edu",
            password_hash=hash_password("Biotech@Password123"),
            subscription_plan="Annual Department License"
        )
        db.activate_department_subscription(bio_id, duration_months=12)
        db.update_department_status(bio_id, status="SUSPENDED", subscription_status="SUSPENDED")
        db.record_audit_log("BIOTECH001 account created and suspended by admin", department_id=bio_id, department_code="BIOTECH001")
        print("[OK] Test Department Created: BIOTECH001 (Status: SUSPENDED)")

    # Department 4: EXPIRED Department (Pharmacy Department - PHARMA001)
    dept_pharma = db.get_department_by_code("PHARMA001")
    if not dept_pharma:
        pharma_id = db.create_department(
            department_name="Pharmacy Department",
            department_code="PHARMA001",
            institution_name="Institute of Pharmaceutical Sciences",
            contact_email="pharma@pharma-inst.edu",
            password_hash=hash_password("Pharma@Password123"),
            subscription_plan="Monthly Department Pass"
        )
        # Set subscription end in past (e.g. 30 days ago)
        past_start = datetime.datetime.now() - datetime.timedelta(days=60)
        past_end = datetime.datetime.now() - datetime.timedelta(days=30)
        
        with db.get_db_cursor() as (cursor, conn):
            cursor.execute("""
                UPDATE departments SET 
                    status = 'EXPIRED',
                    subscription_status = 'EXPIRED',
                    payment_status = 'PAID',
                    subscription_start = ?,
                    subscription_end = ?
                WHERE id = ?
            """, (past_start, past_end, pharma_id))

        db.record_audit_log("PHARMA001 account created with expired subscription", department_id=pharma_id, department_code="PHARMA001")
        print("[OK] Test Department Created: PHARMA001 (Status: EXPIRED)")

    print("==========================================================")
    print("[OK] DATABASE SEEDING COMPLETED SUCCESSFULLY")
    print("==========================================================")

if __name__ == "__main__":
    seed_database()
