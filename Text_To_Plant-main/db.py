"""
db.py
Database abstraction and management layer for Department-Based Plant Identification Portal.
Supports PostgreSQL (via DATABASE_URL for Vercel/Supabase/Neon) with automatic zero-config SQLite fallback.
"""

import os
import re
import sqlite3
import datetime
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Check if PostgreSQL is specified
IS_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")

if IS_POSTGRES:
    # Normalize postgres:// to postgresql:// for SQLAlchemy/psycopg2 compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Default local SQLite path
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_to_plant.db")
# If running on Vercel and no Postgres DATABASE_URL is set, use /tmp
if (os.environ.get("VERCEL") == "1" or "VERCEL" in os.environ) and not IS_POSTGRES:
    LOCAL_DB_PATH = "/tmp/text_to_plant.db"


def get_db_connection():
    """
    Returns a database connection (PostgreSQL if DATABASE_URL configured, else SQLite).
    """
    if IS_POSTGRES:
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        except ImportError:
            # Fall back to sqlite if psycopg2 is not installed locally
            pass
        except Exception as e:
            print(f"[DB WARN] Failed to connect to PostgreSQL ({e}), falling back to SQLite.")
    
    # SQLite Connection with row factory for dictionary-like access
    conn = sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor():
    """
    Context manager that yields a cursor and automatically handles commits and rollbacks.
    """
    conn = get_db_connection()
    try:
        if IS_POSTGRES and hasattr(conn, 'cursor'):
            try:
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            except Exception:
                cursor = conn.cursor()
        else:
            cursor = conn.cursor()
        
        yield cursor, conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def dict_from_row(row):
    """Converts a sqlite3.Row or psycopg2 DictRow to a standard python dict."""
    if row is None:
        return None
    return dict(row)


def dicts_from_rows(rows):
    """Converts a list of rows to a list of standard python dicts."""
    if not rows:
        return []
    return [dict(r) for r in rows]


def init_database_tables():
    """
    Initializes all database tables: admins, departments, payments, subscription_plans, audit_logs.
    Uses generic SQL compatible with both PostgreSQL and SQLite.
    """
    with get_db_cursor() as (cursor, conn):
        # 1. Admins Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """ if not IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # 2. Subscription Plans Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                duration_months INTEGER NOT NULL,
                price REAL NOT NULL,
                currency VARCHAR(10) DEFAULT 'INR',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """ if not IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                duration_months INTEGER NOT NULL,
                price REAL NOT NULL,
                currency VARCHAR(10) DEFAULT 'INR',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Departments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_name VARCHAR(255) NOT NULL,
                department_code VARCHAR(100) UNIQUE NOT NULL,
                institution_name VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'PENDING',
                subscription_status VARCHAR(50) DEFAULT 'PENDING',
                payment_status VARCHAR(50) DEFAULT 'PENDING',
                subscription_plan VARCHAR(100) DEFAULT '12 Months',
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """ if not IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                department_name VARCHAR(255) NOT NULL,
                department_code VARCHAR(100) UNIQUE NOT NULL,
                institution_name VARCHAR(255) NOT NULL,
                contact_email VARCHAR(255) NOT NULL,
                password_hash TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'PENDING',
                subscription_status VARCHAR(50) DEFAULT 'PENDING',
                payment_status VARCHAR(50) DEFAULT 'PENDING',
                subscription_plan VARCHAR(100) DEFAULT '12 Months',
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # 4. Payments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INTEGER NOT NULL,
                payment_reference VARCHAR(255) UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency VARCHAR(10) DEFAULT 'INR',
                payment_status VARCHAR(50) DEFAULT 'PENDING',
                payment_date TIMESTAMP,
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                gateway_reference VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
            )
        """ if not IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
                payment_reference VARCHAR(255) UNIQUE NOT NULL,
                amount REAL NOT NULL,
                currency VARCHAR(10) DEFAULT 'INR',
                payment_status VARCHAR(50) DEFAULT 'PENDING',
                payment_date TIMESTAMP,
                subscription_start TIMESTAMP,
                subscription_end TIMESTAMP,
                gateway_reference VARCHAR(255),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Audit Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INTEGER,
                department_code VARCHAR(100),
                action TEXT NOT NULL,
                ip_address VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """ if not IS_POSTGRES else """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                department_id INTEGER,
                department_code VARCHAR(100),
                action TEXT NOT NULL,
                ip_address VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

# =====================================================
# DEPARTMENT HELPER QUERIES
# =====================================================

def get_department_by_code(department_code):
    """Fetch department record by department code (case-insensitive with 0/O typo tolerance)."""
    if not department_code:
        return None
    code_clean = str(department_code).strip().upper()
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "SELECT * FROM departments WHERE UPPER(department_code) = ? LIMIT 1" if not IS_POSTGRES
            else "SELECT * FROM departments WHERE UPPER(department_code) = %s LIMIT 1",
            (code_clean,)
        )
        row = cursor.fetchone()
        if row:
            return dict_from_row(row)
        
        # Fallback: Check with letter O replaced by digit 0 (e.g. BOTANYOO1 -> BOTANY001)
        normalized_code = re.sub(r'([A-Z]+)O+([0-9]*)', lambda m: m.group(1) + '0' * len(re.findall(r'O', m.group(0))) + m.group(2), code_clean)
        if normalized_code != code_clean:
            cursor.execute(
                "SELECT * FROM departments WHERE UPPER(department_code) = ? LIMIT 1" if not IS_POSTGRES
                else "SELECT * FROM departments WHERE UPPER(department_code) = %s LIMIT 1",
                (normalized_code,)
            )
            row = cursor.fetchone()
            if row:
                return dict_from_row(row)

        return None


def get_department_by_id(department_id):
    """Fetch department record by numeric ID."""
    if not department_id:
        return None
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "SELECT * FROM departments WHERE id = ? LIMIT 1" if not IS_POSTGRES
            else "SELECT * FROM departments WHERE id = %s LIMIT 1",
            (int(department_id),)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def get_all_departments():
    """Retrieve all departments ordered by creation date descending."""
    with get_db_cursor() as (cursor, _):
        cursor.execute("SELECT * FROM departments ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def create_department(department_name, department_code, institution_name, contact_email, password_hash, subscription_plan="12 Months"):
    """
    Creates a new department with initial status = 'PENDING', payment_status = 'PENDING'.
    Returns the newly created department ID.
    """
    code_clean = str(department_code).strip().upper()
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with get_db_cursor() as (cursor, _):
        if not IS_POSTGRES:
            cursor.execute("""
                INSERT INTO departments (
                    department_name, department_code, institution_name, contact_email,
                    password_hash, status, subscription_status, payment_status,
                    subscription_plan, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 'PENDING', 'PENDING', ?, ?, ?)
            """, (
                department_name.strip(), code_clean, institution_name.strip(),
                contact_email.strip().lower(), password_hash, subscription_plan, now_iso, now_iso
            ))
            return cursor.lastrowid
        else:
            cursor.execute("""
                INSERT INTO departments (
                    department_name, department_code, institution_name, contact_email,
                    password_hash, status, subscription_status, payment_status,
                    subscription_plan, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, 'PENDING', 'PENDING', 'PENDING', %s, %s, %s)
                RETURNING id
            """, (
                department_name.strip(), code_clean, institution_name.strip(),
                contact_email.strip().lower(), password_hash, subscription_plan, now_iso, now_iso
            ))
            row = cursor.fetchone()
            return row[0] if row else None


def update_department_status(department_id, status, subscription_status=None, payment_status=None):
    """Updates the status flags of a department."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        query = "UPDATE departments SET status = ?, updated_at = ?"
        params = [status, now_iso]

        if subscription_status is not None:
            query += ", subscription_status = ?"
            params.append(subscription_status)
        if payment_status is not None:
            query += ", payment_status = ?"
            params.append(payment_status)

        query += " WHERE id = ?"
        params.append(int(department_id))

        if IS_POSTGRES:
            query = query.replace("?", "%s")

        cursor.execute(query, tuple(params))


def update_department_password(department_id, password_hash):
    """Updates the password hash of a department."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "UPDATE departments SET password_hash = ?, updated_at = ? WHERE id = ?" if not IS_POSTGRES
            else "UPDATE departments SET password_hash = %s, updated_at = %s WHERE id = %s",
            (password_hash, now_iso, int(department_id))
        )


def update_department_last_login(department_id):
    """Updates the last_login timestamp of a department."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "UPDATE departments SET last_login = ? WHERE id = ?" if not IS_POSTGRES
            else "UPDATE departments SET last_login = %s WHERE id = %s",
            (now_iso, int(department_id))
        )


def activate_department_subscription(department_id, duration_months=12, start_from=None):
    """
    Activates/extends department subscription by duration_months.
    Sets status = 'ACTIVE', subscription_status = 'ACTIVE', payment_status = 'PAID'.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    if start_from and start_from > now:
        sub_start = start_from
    else:
        sub_start = now
    
    # Calculate end date (+duration_months approximately)
    # 30.5 days per month average or approximate date calculation
    sub_end = sub_start + datetime.timedelta(days=int(duration_months * 30.5))
    
    sub_start_str = sub_start.strftime("%Y-%m-%d %H:%M:%S")
    sub_end_str = sub_end.strftime("%Y-%m-%d %H:%M:%S")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    with get_db_cursor() as (cursor, _):
        cursor.execute("""
            UPDATE departments 
            SET status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = ?,
                subscription_end = ?,
                updated_at = ?
            WHERE id = ?
        """ if not IS_POSTGRES else """
            UPDATE departments 
            SET status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = %s,
                subscription_end = %s,
                updated_at = %s
            WHERE id = %s
        """, (sub_start_str, sub_end_str, now_str, int(department_id)))

    return sub_start_str, sub_end_str


def delete_department(department_id):
    """Deletes a department and associated records."""
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "DELETE FROM departments WHERE id = ?" if not IS_POSTGRES
            else "DELETE FROM departments WHERE id = %s",
            (int(department_id),)
        )


# =====================================================
# PAYMENT HELPER QUERIES
# =====================================================

def create_payment_record(department_id, payment_reference, amount, currency="INR", duration_months=12, notes=None):
    """Creates a new payment record (initial status = 'PENDING')."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        if not IS_POSTGRES:
            cursor.execute("""
                INSERT INTO payments (
                    department_id, payment_reference, amount, currency,
                    payment_status, notes, created_at
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
            """, (int(department_id), payment_reference, float(amount), currency, notes, now_iso))
            return cursor.lastrowid
        else:
            cursor.execute("""
                INSERT INTO payments (
                    department_id, payment_reference, amount, currency,
                    payment_status, notes, created_at
                ) VALUES (%s, %s, %s, %s, 'PENDING', %s, %s)
                RETURNING id
            """, (int(department_id), payment_reference, float(amount), currency, notes, now_iso))
            row = cursor.fetchone()
            return row[0] if row else None


def get_payment_by_reference(payment_reference):
    """Fetch payment record by unique reference code."""
    if not payment_reference:
        return None
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "SELECT * FROM payments WHERE payment_reference = ? LIMIT 1" if not IS_POSTGRES
            else "SELECT * FROM payments WHERE payment_reference = %s LIMIT 1",
            (str(payment_reference).strip(),)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def get_payments_for_department(department_id):
    """Retrieve all payment records for a specific department."""
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "SELECT * FROM payments WHERE department_id = ? ORDER BY created_at DESC" if not IS_POSTGRES
            else "SELECT * FROM payments WHERE department_id = %s ORDER BY created_at DESC",
            (int(department_id),)
        )
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def get_all_payments():
    """Retrieve all payments across all departments join with department names."""
    with get_db_cursor() as (cursor, _):
        cursor.execute("""
            SELECT p.*, d.department_name, d.department_code, d.institution_name
            FROM payments p
            LEFT JOIN departments d ON p.department_id = d.id
            ORDER BY p.created_at DESC
        """)
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def mark_payment_verified(payment_reference, gateway_reference=None, duration_months=12):
    """
    Marks payment as PAID, activates department subscription, and updates subscription dates.
    """
    payment = get_payment_by_reference(payment_reference)
    if not payment:
        return False, "Payment reference not found."
    
    dept_id = payment["department_id"]
    dept = get_department_by_id(dept_id)
    if not dept:
        return False, "Associated department not found."

    # Determine start date (if dept has existing valid subscription, extend from that date)
    now = datetime.datetime.now(datetime.timezone.utc)
    start_from = now
    if dept.get("subscription_end"):
        try:
            current_sub_end = datetime.datetime.fromisoformat(str(dept["subscription_end"]).replace("Z", "+00:00"))
            if current_sub_end.tzinfo is None:
                current_sub_end = current_sub_end.replace(tzinfo=datetime.timezone.utc)
            if current_sub_end > now:
                start_from = current_sub_end
        except Exception:
            pass

    sub_start_str, sub_end_str = activate_department_subscription(dept_id, duration_months=duration_months, start_from=start_from)

    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        cursor.execute("""
            UPDATE payments
            SET payment_status = 'PAID',
                payment_date = ?,
                subscription_start = ?,
                subscription_end = ?,
                gateway_reference = ?
            WHERE payment_reference = ?
        """ if not IS_POSTGRES else """
            UPDATE payments
            SET payment_status = 'PAID',
                payment_date = %s,
                subscription_start = %s,
                subscription_end = %s,
                gateway_reference = %s
            WHERE payment_reference = %s
        """, (now_iso, sub_start_str, sub_end_str, gateway_reference or "MANUAL_VERIFIED", payment_reference))

    return True, "Payment verified successfully and department activated."


# =====================================================
# ADMIN & SUBSCRIPTION PLAN HELPER QUERIES
# =====================================================

def get_admin_by_username(username):
    """Fetch admin by username."""
    if not username:
        return None
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "SELECT * FROM admins WHERE LOWER(username) = ? LIMIT 1" if not IS_POSTGRES
            else "SELECT * FROM admins WHERE LOWER(username) = %s LIMIT 1",
            (str(username).strip().lower(),)
        )
        row = cursor.fetchone()
        return dict_from_row(row)


def create_admin(username, password_hash):
    """Creates a new administrator account."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        if not IS_POSTGRES:
            cursor.execute("""
                INSERT INTO admins (username, password_hash, created_at)
                VALUES (?, ?, ?)
            """, (str(username).strip().lower(), password_hash, now_iso))
            return cursor.lastrowid
        else:
            cursor.execute("""
                INSERT INTO admins (username, password_hash, created_at)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (str(username).strip().lower(), password_hash, now_iso))
            row = cursor.fetchone()
            return row[0] if row else None


def update_admin_last_login(admin_id):
    """Updates admin last login timestamp."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            "UPDATE admins SET last_login = ? WHERE id = ?" if not IS_POSTGRES
            else "UPDATE admins SET last_login = %s WHERE id = %s",
            (now_iso, int(admin_id))
        )


def get_all_subscription_plans():
    """Retrieve all active subscription plans."""
    with get_db_cursor() as (cursor, _):
        cursor.execute("SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY duration_months ASC")
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def create_subscription_plan(name, duration_months, price, currency="INR"):
    """Adds a new subscription plan."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_db_cursor() as (cursor, _):
        if not IS_POSTGRES:
            cursor.execute("""
                INSERT INTO subscription_plans (name, duration_months, price, currency, is_active, created_at)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (name.strip(), int(duration_months), float(price), currency.strip(), now_iso))
            return cursor.lastrowid
        else:
            cursor.execute("""
                INSERT INTO subscription_plans (name, duration_months, price, currency, is_active, created_at)
                VALUES (%s, %s, %s, %s, 1, %s)
                RETURNING id
            """, (name.strip(), int(duration_months), float(price), currency.strip(), now_iso))
            row = cursor.fetchone()
            return row[0] if row else None


# =====================================================
# AUDIT LOGGING HELPER QUERIES
# =====================================================

def record_audit_log(action, department_id=None, department_code=None, ip_address=None):
    """Records an event into the audit_logs table."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with get_db_cursor() as (cursor, _):
            if not IS_POSTGRES:
                cursor.execute("""
                    INSERT INTO audit_logs (department_id, department_code, action, ip_address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (department_id, department_code, action, ip_address, now_iso))
            else:
                cursor.execute("""
                    INSERT INTO audit_logs (department_id, department_code, action, ip_address, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (department_id, department_code, action, ip_address, now_iso))
    except Exception as e:
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")


def get_recent_audit_logs(limit=50):
    """Retrieve the most recent audit logs."""
    with get_db_cursor() as (cursor, _):
        cursor.execute(
            f"SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT {int(limit)}"
        )
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def get_dashboard_metrics():
    """
    Calculates summary metrics for the Admin Dashboard:
    - Total departments, Active, Pending, Expired, Suspended count
    - Total payments count and Total revenue
    """
    with get_db_cursor() as (cursor, _):
        cursor.execute("SELECT status, COUNT(*) as count FROM departments GROUP BY status")
        dept_counts = {r['status'].upper(): r['count'] for r in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) as total FROM departments")
        total_depts = cursor.fetchone()['total'] or 0

        cursor.execute("SELECT COUNT(*) as total_payments, SUM(amount) as total_revenue FROM payments WHERE payment_status = 'PAID'")
        pay_row = cursor.fetchone()
        total_payments = pay_row['total_payments'] or 0
        total_revenue = pay_row['total_revenue'] or 0.0

        return {
            "total_departments": total_depts,
            "active_departments": dept_counts.get("ACTIVE", 0),
            "pending_departments": dept_counts.get("PENDING", 0),
            "expired_departments": dept_counts.get("EXPIRED", 0),
            "suspended_departments": dept_counts.get("SUSPENDED", 0),
            "total_payments": total_payments,
            "total_revenue": round(float(total_revenue), 2)
        }
