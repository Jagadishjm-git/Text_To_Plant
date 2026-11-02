"""
db.py
Database abstraction and management layer for Department-Based Plant Identification Portal.
Supports MongoDB (via MONGO_URI / MONGODB_URI / DATABASE_URL) as primary,
with automatic PostgreSQL and zero-config SQLite fallbacks.
"""

import os
import re
import sqlite3
import datetime
from contextlib import contextmanager

# =====================================================
# AUTOMATIC ENVIRONMENT LOADING (.env & venv/.env)
# =====================================================

def _load_project_env():
    """Loads variables from .env or venv/.env into os.environ."""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(cur_dir, ".env"),
        os.path.join(cur_dir, "venv", ".env")
    ]
    # Try using python-dotenv if available
    try:
        from dotenv import load_dotenv
        for env_path in candidates:
            if os.path.isfile(env_path):
                load_dotenv(env_path, override=False)
    except Exception:
        pass

    # Direct fallback file reader
    for env_path in candidates:
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as ef:
                    for line in ef:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_project_env()

# =====================================================
# DATABASE CONFIGURATION & DETECTION
# =====================================================

def get_mongo_uri():
    """Retrieves current MongoDB URI from environment variables."""
    uri = os.environ.get("MONGO_URI", os.environ.get("MONGODB_URI", "")).strip()
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not uri and (db_url.startswith("mongodb://") or db_url.startswith("mongodb+srv://") or db_url.startswith("mongomock://")):
        uri = db_url
    if uri:
        # Strip accidental placeholder brackets around password like <password>
        uri = re.sub(r':<([^>]+)>@', r':\1@', uri)
    return uri

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
MONGO_URI = get_mongo_uri()
IS_MONGO = bool(MONGO_URI)

# Check if PostgreSQL is specified
IS_POSTGRES = not IS_MONGO and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"))

if IS_POSTGRES:
    # Normalize postgres:// to postgresql:// for SQLAlchemy/psycopg2 compatibility
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Default local SQLite path
LOCAL_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "text_to_plant.db")
# If running on Vercel, always use /tmp for SQLite (Vercel's /var/task is read-only)
IS_VERCEL_ENV = os.environ.get("VERCEL") == "1" or "VERCEL" in os.environ
if IS_VERCEL_ENV:
    LOCAL_DB_PATH = "/tmp/text_to_plant.db"


# =====================================================
# MONGODB CONNECTION & HELPERS
# =====================================================

_mongo_client = None
_mongo_db = None
_mongo_last_failure = 0.0
_MONGO_FAIL_COOLDOWN = 15.0  # seconds cooldown before retrying unreachable cluster

def get_mongo_db():
    """
    Returns active MongoDB database object if MONGO_URI is configured and reachable.
    Caches connection and applies a cooldown on failed attempts to prevent latency spikes.
    """
    global _mongo_client, _mongo_db, _mongo_last_failure
    current_uri = get_mongo_uri()
    if not current_uri:
        return None
    if _mongo_db is not None:
        return _mongo_db

    import time
    now_ts = time.time()
    if now_ts - _mongo_last_failure < _MONGO_FAIL_COOLDOWN:
        return None

    try:
        # Check for in-memory mongomock URI
        if current_uri.startswith("mongomock://"):
            import mongomock
            _mongo_client = mongomock.MongoClient()
            _mongo_db = _mongo_client["text_to_plant"]
            print("[DB INFO] Connected to in-memory mongomock database.")
            return _mongo_db

        import pymongo
        _mongo_client = pymongo.MongoClient(
            current_uri,
            serverSelectionTimeoutMS=2500,
            connectTimeoutMS=2500,
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        # Verify connection
        _mongo_client.admin.command('ping')
        try:
            _mongo_db = _mongo_client.get_default_database()
        except Exception:
            _mongo_db = None
        if _mongo_db is None:
            _mongo_db = _mongo_client["text_to_plant"]
        print("[DB INFO] Successfully connected to MongoDB cluster.")
        return _mongo_db
    except Exception as e:
        _mongo_last_failure = now_ts
        print(f"[DB WARN] Failed to connect to MongoDB ({e}), falling back to SQL.")
        return None


def is_mongo_active():
    """Returns True if MongoDB is configured and responsive."""
    return get_mongo_db() is not None


def get_database_info():
    """Returns metadata about the active database backend."""
    if is_mongo_active():
        uri = get_mongo_uri()
        masked_uri = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', uri) if uri else "MongoDB"
        return {"engine": "MongoDB", "active": True, "connection": masked_uri}
    elif IS_POSTGRES:
        return {"engine": "PostgreSQL", "active": True, "connection": "PostgreSQL Remote"}
    else:
        return {"engine": "SQLite", "active": True, "connection": LOCAL_DB_PATH}


def serialize_mongo_doc(doc):
    """
    Converts MongoDB BSON document to a standard Python dictionary.
    Formats BSON datetimes to strings to prevent template and JSON serialization errors.
    """
    if not doc:
        return None
    d = dict(doc)
    if "_id" in d:
        if "id" not in d:
            d["id"] = str(d["_id"])
        d["_id"] = str(d["_id"])
    for k, v in list(d.items()):
        if isinstance(v, (datetime.datetime, datetime.date)):
            d[k] = v.strftime("%Y-%m-%d %H:%M:%S")
    return d


def get_next_mongo_id(collection_name):
    """Generates sequential integer IDs in MongoDB for backwards compatibility."""
    mdb = get_mongo_db()
    if mdb is None:
        return 1
    from pymongo import ReturnDocument
    counter = mdb["counters"].find_one_and_update(
        {"_id": collection_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return counter["seq"]



# =====================================================
# SQL CONNECTION & HELPERS (POSTGRES / SQLITE FALLBACK)
# =====================================================

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


# =====================================================
# SCHEMA INITIALIZATION
# =====================================================

def init_database_tables():
    """
    Initializes database tables (SQL) or collections & indexes (MongoDB).
    """
    if is_mongo_active():
        mdb = get_mongo_db()
        try:
            mdb["admins"].create_index("username", unique=True)
            mdb["departments"].create_index("department_code", unique=True)
            mdb["departments"].create_index("id", unique=True)
            mdb["payments"].create_index("payment_reference", unique=True)
            mdb["payments"].create_index("department_id")
            mdb["subscription_plans"].create_index("name")
            mdb["audit_logs"].create_index("created_at")
            print("[DB INFO] MongoDB collections and unique indexes initialized.")
        except Exception as e:
            print(f"[DB WARN] MongoDB index setup warning: {e}")
        return

    # SQL fallback
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
# ADMIN DATA ACCESS METHODS
# =====================================================

def get_admin_by_username(username):
    if not username:
        return None
    if is_mongo_active():
        mdb = get_mongo_db()
        doc = mdb["admins"].find_one({"username": {"$regex": f"^{re.escape(username.strip())}$", "$options": "i"}})
        return serialize_mongo_doc(doc)
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM admins WHERE LOWER(username) = LOWER(%s)" if IS_POSTGRES else "SELECT * FROM admins WHERE LOWER(username) = LOWER(?)", (username,))
        row = cursor.fetchone()
        return dict_from_row(row)


def create_admin(username, password_hash):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        new_id = get_next_mongo_id("admins")
        mdb["admins"].insert_one({
            "id": new_id,
            "username": username.strip().lower(),
            "password_hash": password_hash,
            "created_at": now,
            "last_login": None
        })
        return new_id
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (%s, %s) RETURNING id" if IS_POSTGRES else "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
        if not IS_POSTGRES:
            return cursor.lastrowid
        else:
            return cursor.fetchone()[0]


def update_admin_last_login(admin_id):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(admin_id) if str(admin_id).isdigit() else admin_id
        mdb["admins"].update_one({"id": match_id}, {"$set": {"last_login": now}})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute("UPDATE admins SET last_login = %s WHERE id = %s" if IS_POSTGRES else "UPDATE admins SET last_login = ? WHERE id = ?", (now, admin_id))


# =====================================================
# DEPARTMENT DATA ACCESS METHODS
# =====================================================

def get_department_by_id(dept_id):
    if not dept_id:
        return None
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        doc = mdb["departments"].find_one({"id": match_id})
        return serialize_mongo_doc(doc)
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM departments WHERE id = %s" if IS_POSTGRES else "SELECT * FROM departments WHERE id = ?", (dept_id,))
        row = cursor.fetchone()
        return dict_from_row(row)


def get_department_by_code(dept_code):
    if not dept_code:
        return None
    dept_code = dept_code.strip().upper()
    if is_mongo_active():
        mdb = get_mongo_db()
        doc = mdb["departments"].find_one({"department_code": dept_code})
        return serialize_mongo_doc(doc)
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM departments WHERE UPPER(department_code) = %s" if IS_POSTGRES else "SELECT * FROM departments WHERE UPPER(department_code) = ?", (dept_code,))
        row = cursor.fetchone()
        return dict_from_row(row)


def get_all_departments():
    if is_mongo_active():
        mdb = get_mongo_db()
        docs = list(mdb["departments"].find().sort("created_at", -1))
        return [serialize_mongo_doc(d) for d in docs]
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM departments ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def create_department(department_name, department_code, institution_name, contact_email, password_hash, subscription_plan="Annual Department License"):
    dept_code = department_code.strip().upper()
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        new_id = get_next_mongo_id("departments")
        doc = {
            "id": new_id,
            "department_name": department_name,
            "department_code": dept_code,
            "institution_name": institution_name,
            "contact_email": contact_email,
            "password_hash": password_hash,
            "status": "PENDING",
            "subscription_status": "PENDING",
            "payment_status": "PENDING",
            "subscription_plan": subscription_plan,
            "subscription_start": None,
            "subscription_end": None,
            "created_at": now,
            "updated_at": now,
            "last_login": None
        }
        mdb["departments"].insert_one(doc)
        return new_id
    with get_db_cursor() as (cursor, conn):
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO departments (
                    department_name, department_code, institution_name, contact_email, 
                    password_hash, status, subscription_status, payment_status, subscription_plan, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, 'PENDING', 'PENDING', 'PENDING', %s, %s, %s) RETURNING id
            """, (department_name, dept_code, institution_name, contact_email, password_hash, subscription_plan, now, now))
            new_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO departments (
                    department_name, department_code, institution_name, contact_email, 
                    password_hash, status, subscription_status, payment_status, subscription_plan, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 'PENDING', 'PENDING', ?, ?, ?)
            """, (department_name, dept_code, institution_name, contact_email, password_hash, subscription_plan, now, now))
            new_id = cursor.lastrowid
        return new_id


def update_department_status(dept_id, status, subscription_status=None, payment_status=None):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        update_fields = {"status": status, "updated_at": now}
        if subscription_status:
            update_fields["subscription_status"] = subscription_status
        if payment_status:
            update_fields["payment_status"] = payment_status
        mdb["departments"].update_one({"id": match_id}, {"$set": update_fields})
        return
    with get_db_cursor() as (cursor, conn):
        if subscription_status and payment_status:
            cursor.execute(
                "UPDATE departments SET status = %s, subscription_status = %s, payment_status = %s, updated_at = %s WHERE id = %s" if IS_POSTGRES else
                "UPDATE departments SET status = ?, subscription_status = ?, payment_status = ?, updated_at = ? WHERE id = ?",
                (status, subscription_status, payment_status, now, dept_id)
            )
        elif subscription_status:
            cursor.execute(
                "UPDATE departments SET status = %s, subscription_status = %s, updated_at = %s WHERE id = %s" if IS_POSTGRES else
                "UPDATE departments SET status = ?, subscription_status = ?, updated_at = ? WHERE id = ?",
                (status, subscription_status, now, dept_id)
            )
        else:
            cursor.execute(
                "UPDATE departments SET status = %s, updated_at = %s WHERE id = %s" if IS_POSTGRES else
                "UPDATE departments SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, dept_id)
            )


def update_department_password(dept_id, new_password_hash):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        mdb["departments"].update_one({"id": match_id}, {"$set": {"password_hash": new_password_hash, "updated_at": now}})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute(
            "UPDATE departments SET password_hash = %s, updated_at = %s WHERE id = %s" if IS_POSTGRES else
            "UPDATE departments SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_password_hash, now, dept_id)
        )


def update_department_last_login(dept_id):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        mdb["departments"].update_one({"id": match_id}, {"$set": {"last_login": now}})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute("UPDATE departments SET last_login = %s WHERE id = %s" if IS_POSTGRES else "UPDATE departments SET last_login = ? WHERE id = ?", (now, dept_id))


def delete_department(dept_id):
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        mdb["departments"].delete_one({"id": match_id})
        mdb["payments"].delete_many({"department_id": match_id})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute("DELETE FROM departments WHERE id = %s" if IS_POSTGRES else "DELETE FROM departments WHERE id = ?", (dept_id,))


def activate_department_subscription(dept_id, duration_months=12):
    now = datetime.datetime.now()
    end_date = now + datetime.timedelta(days=30 * duration_months)
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        mdb["departments"].update_one({"id": match_id}, {"$set": {
            "status": "ACTIVE",
            "subscription_status": "ACTIVE",
            "payment_status": "PAID",
            "subscription_start": now,
            "subscription_end": end_date,
            "updated_at": now
        }})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE departments SET 
                status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = %s,
                subscription_end = %s,
                updated_at = %s
            WHERE id = %s
        """ if IS_POSTGRES else """
            UPDATE departments SET 
                status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = ?,
                subscription_end = ?,
                updated_at = ?
            WHERE id = ?
        """, (now, end_date, now, dept_id))


def extend_department_subscription(dept_id, duration_months=12):
    dept = get_department_by_id(dept_id)
    if not dept:
        return None
    
    now = datetime.datetime.now()
    current_end = dept.get("subscription_end")
    if current_end:
        if isinstance(current_end, str):
            try:
                current_end = datetime.datetime.strptime(current_end.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except Exception:
                current_end = now
        start_from = max(now, current_end)
    else:
        start_from = now

    new_end_date = start_from + datetime.timedelta(days=30 * duration_months)
    start_date = dept.get("subscription_start") or now

    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        mdb["departments"].update_one({"id": match_id}, {"$set": {
            "status": "ACTIVE",
            "subscription_status": "ACTIVE",
            "payment_status": "PAID",
            "subscription_start": start_date,
            "subscription_end": new_end_date,
            "updated_at": now
        }})
        return
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE departments SET 
                status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = %s,
                subscription_end = %s,
                updated_at = %s
            WHERE id = %s
        """ if IS_POSTGRES else """
            UPDATE departments SET 
                status = 'ACTIVE',
                subscription_status = 'ACTIVE',
                payment_status = 'PAID',
                subscription_start = ?,
                subscription_end = ?,
                updated_at = ?
            WHERE id = ?
        """, (start_date, new_end_date, now, dept_id))


# =====================================================
# PAYMENT & SUBSCRIPTION DATA ACCESS METHODS
# =====================================================

def create_payment_record(department_id, payment_reference, amount, currency="INR", duration_months=12, notes=None):
    now = datetime.datetime.now()
    sub_start = now
    sub_end = now + datetime.timedelta(days=30 * duration_months)
    match_dept_id = int(department_id) if str(department_id).isdigit() else department_id
    if is_mongo_active():
        mdb = get_mongo_db()
        new_id = get_next_mongo_id("payments")
        doc = {
            "id": new_id,
            "department_id": match_dept_id,
            "payment_reference": payment_reference,
            "amount": float(amount),
            "currency": currency,
            "payment_status": "PENDING",
            "payment_date": None,
            "subscription_start": sub_start,
            "subscription_end": sub_end,
            "gateway_reference": None,
            "notes": notes,
            "created_at": now
        }
        mdb["payments"].insert_one(doc)
        return new_id
    with get_db_cursor() as (cursor, conn):
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO payments (
                    department_id, payment_reference, amount, currency, payment_status,
                    subscription_start, subscription_end, notes, created_at
                ) VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, %s, %s) RETURNING id
            """, (department_id, payment_reference, amount, currency, sub_start, sub_end, notes, now))
            return cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO payments (
                    department_id, payment_reference, amount, currency, payment_status,
                    subscription_start, subscription_end, notes, created_at
                ) VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """, (department_id, payment_reference, amount, currency, sub_start, sub_end, notes, now))
            return cursor.lastrowid


def get_payment_by_reference(payment_ref):
    if is_mongo_active():
        mdb = get_mongo_db()
        doc = mdb["payments"].find_one({"payment_reference": payment_ref})
        return serialize_mongo_doc(doc)
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM payments WHERE payment_reference = %s" if IS_POSTGRES else "SELECT * FROM payments WHERE payment_reference = ?", (payment_ref,))
        row = cursor.fetchone()
        return dict_from_row(row)


def get_payments_for_department(dept_id):
    if is_mongo_active():
        mdb = get_mongo_db()
        match_id = int(dept_id) if str(dept_id).isdigit() else dept_id
        docs = list(mdb["payments"].find({"department_id": match_id}).sort("created_at", -1))
        return [serialize_mongo_doc(d) for d in docs]
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM payments WHERE department_id = %s ORDER BY created_at DESC" if IS_POSTGRES else "SELECT * FROM payments WHERE department_id = ? ORDER BY created_at DESC", (dept_id,))
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def get_all_payments():
    if is_mongo_active():
        mdb = get_mongo_db()
        payments = list(mdb["payments"].find().sort("created_at", -1))
        result = []
        for p in payments:
            sp = serialize_mongo_doc(p)
            dept = get_department_by_id(sp.get("department_id"))
            if dept:
                sp["department_name"] = dept.get("department_name", "")
                sp["department_code"] = dept.get("department_code", "")
                sp["institution_name"] = dept.get("institution_name", "")
            else:
                sp["department_name"] = ""
                sp["department_code"] = ""
                sp["institution_name"] = ""
            result.append(sp)
        return result
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            SELECT p.*, d.department_name, d.department_code, d.institution_name 
            FROM payments p
            JOIN departments d ON p.department_id = d.id
            ORDER BY p.created_at DESC
        """)
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


def mark_payment_verified(payment_ref, gateway_reference="TXN_SIMULATED_GATEWAY_OK", duration_months=12):
    pay = get_payment_by_reference(payment_ref)
    if not pay:
        return False
    
    now = datetime.datetime.now()
    sub_start = now
    sub_end = now + datetime.timedelta(days=30 * duration_months)

    if is_mongo_active():
        mdb = get_mongo_db()
        mdb["payments"].update_one(
            {"payment_reference": payment_ref},
            {"$set": {
                "payment_status": "PAID",
                "payment_date": now,
                "subscription_start": sub_start,
                "subscription_end": sub_end,
                "gateway_reference": gateway_reference
            }}
        )
        extend_department_subscription(pay["department_id"], duration_months=duration_months)
        return True

    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            UPDATE payments SET 
                payment_status = 'PAID',
                payment_date = %s,
                subscription_start = %s,
                subscription_end = %s,
                gateway_reference = %s
            WHERE payment_reference = %s
        """ if IS_POSTGRES else """
            UPDATE payments SET 
                payment_status = 'PAID',
                payment_date = ?,
                subscription_start = ?,
                subscription_end = ?,
                gateway_reference = ?
            WHERE payment_reference = ?
        """, (now, sub_start, sub_end, gateway_reference, payment_ref))

    # Activate department
    extend_department_subscription(pay["department_id"], duration_months=duration_months)
    return True


def create_subscription_plan(name, duration_months, price, currency="INR"):
    now = datetime.datetime.now()
    if is_mongo_active():
        mdb = get_mongo_db()
        new_id = get_next_mongo_id("subscription_plans")
        doc = {
            "id": new_id,
            "name": name,
            "duration_months": int(duration_months),
            "price": float(price),
            "currency": currency,
            "is_active": 1,
            "created_at": now
        }
        mdb["subscription_plans"].insert_one(doc)
        return new_id
    with get_db_cursor() as (cursor, conn):
        if IS_POSTGRES:
            cursor.execute(
                "INSERT INTO subscription_plans (name, duration_months, price, currency) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, duration_months, price, currency)
            )
            return cursor.fetchone()[0]
        else:
            cursor.execute(
                "INSERT INTO subscription_plans (name, duration_months, price, currency) VALUES (?, ?, ?, ?)",
                (name, duration_months, price, currency)
            )
            return cursor.lastrowid


def get_all_subscription_plans():
    if is_mongo_active():
        mdb = get_mongo_db()
        docs = list(mdb["subscription_plans"].find({"is_active": 1}).sort("duration_months", 1))
        return [serialize_mongo_doc(d) for d in docs]
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM subscription_plans WHERE is_active = 1 ORDER BY duration_months ASC")
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


# =====================================================
# AUDIT LOGGING DATA ACCESS METHODS
# =====================================================

def record_audit_log(action, department_id=None, department_code=None, ip_address=None):
    now = datetime.datetime.now()
    match_dept_id = int(department_id) if (department_id and str(department_id).isdigit()) else department_id
    if is_mongo_active():
        mdb = get_mongo_db()
        new_id = get_next_mongo_id("audit_logs")
        doc = {
            "id": new_id,
            "department_id": match_dept_id,
            "department_code": department_code,
            "action": action,
            "ip_address": ip_address,
            "created_at": now
        }
        mdb["audit_logs"].insert_one(doc)
        return new_id
    with get_db_cursor() as (cursor, conn):
        cursor.execute("""
            INSERT INTO audit_logs (department_id, department_code, action, ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """ if IS_POSTGRES else """
            INSERT INTO audit_logs (department_id, department_code, action, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (department_id, department_code, action, ip_address, now))


def get_recent_audit_logs(limit=50):
    if is_mongo_active():
        mdb = get_mongo_db()
        docs = list(mdb["audit_logs"].find().sort("created_at", -1).limit(limit))
        return [serialize_mongo_doc(d) for d in docs]
    with get_db_cursor() as (cursor, conn):
        cursor.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT %s" if IS_POSTGRES else "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return dicts_from_rows(rows)


# =====================================================
# DASHBOARD STATS ANALYTICS
# =====================================================

def get_admin_dashboard_stats():
    departments = get_all_departments()
    payments = get_all_payments()

    total_depts = len(departments)
    active_depts = 0
    pending_depts = 0
    expired_depts = 0
    suspended_depts = 0

    now = datetime.datetime.now()

    for d in departments:
        status = (d.get("status") or "PENDING").upper()
        sub_end = d.get("subscription_end")
        
        # Check dynamic expiration
        is_expired = False
        if sub_end:
            if isinstance(sub_end, str):
                try:
                    sub_end_dt = datetime.datetime.strptime(sub_end.split(".")[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    sub_end_dt = None
            else:
                sub_end_dt = sub_end
            
            if sub_end_dt and now > sub_end_dt:
                is_expired = True

        if status == "SUSPENDED":
            suspended_depts += 1
        elif is_expired or status == "EXPIRED":
            expired_depts += 1
        elif status == "ACTIVE":
            active_depts += 1
        else:
            pending_depts += 1

    total_payments = len([p for p in payments if p.get("payment_status") == "PAID"])
    total_revenue = sum(p.get("amount", 0.0) for p in payments if p.get("payment_status") == "PAID")

    return {
        "total_departments": total_depts,
        "active_departments": active_depts,
        "pending_departments": pending_depts,
        "expired_departments": expired_depts,
        "suspended_departments": suspended_depts,
        "total_payments": total_payments,
        "total_revenue": total_revenue
    }
