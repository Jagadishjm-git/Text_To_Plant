"""
auth.py
Authentication, Password Security & Status Validation Layer for Department-Based Plant Identification Portal.
Provides password hashing (PBKDF2-HMAC-SHA256), session verification decorators, and dynamic subscription expiration evaluation.
"""

import hashlib
import hmac
import os
import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify

import db

# PBKDF2 configuration
SALT_BYTES = 16
ITERATIONS = 100000

def hash_password(password):
    """
    Hashes password using PBKDF2-HMAC-SHA256 with a random salt.
    Format: salt_hex:hash_hex
    """
    if not password:
        return ""
    salt = os.urandom(SALT_BYTES)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f"{salt.hex()}:{pwd_hash.hex()}"


def verify_password(password, stored_hash):
    """
    Verifies a plain-text password against a stored PBKDF2 salt:hash.
    """
    if not password or not stored_hash or ":" not in stored_hash:
        return False
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
        return hmac.compare_digest(computed_hash, expected_hash)
    except Exception as e:
        print(f"[AUTH ERROR] Password verification exception: {e}")
        return False


def evaluate_department_status(department):
    """
    Evaluates the status and subscription of a department.
    Returns tuple: (is_allowed: bool, status_code: str, message: str)
    Possible statuses: ACTIVE, PENDING, SUSPENDED, EXPIRED
    """
    if not department:
        return False, "NOT_FOUND", "Department account not found."

    raw_status = (department.get("status") or "PENDING").upper()
    sub_end = department.get("subscription_end")
    now = datetime.datetime.now()

    # Dynamic Subscription Expiration Check
    if sub_end:
        if isinstance(sub_end, str):
            try:
                sub_end_dt = datetime.datetime.strptime(sub_end.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except Exception:
                sub_end_dt = None
        else:
            sub_end_dt = sub_end

        if sub_end_dt and now > sub_end_dt:
            # Dynamically update department to EXPIRED in database if not suspended
            if raw_status != "SUSPENDED":
                db.update_department_status(department["id"], status="EXPIRED", subscription_status="EXPIRED")
                department["status"] = "EXPIRED"
                department["subscription_status"] = "EXPIRED"
            return False, "EXPIRED", "Your department subscription has expired. Please renew to continue."

    if raw_status == "PENDING":
        return False, "PENDING", "Your department account is awaiting activation."
    elif raw_status == "SUSPENDED":
        return False, "SUSPENDED", "Your department access has been suspended. Please contact the administrator."
    elif raw_status == "EXPIRED":
        return False, "EXPIRED", "Your department subscription has expired. Please renew to continue."
    elif raw_status == "ACTIVE":
        return True, "ACTIVE", "Access granted."

    return False, "UNKNOWN", "Department status invalid."


def department_required(f):
    """
    Decorator for Flask routes requiring a logged-in, ACTIVE department.
    Checks session department_id, validates account exists, and evaluates active subscription status.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        dept_id = session.get("department_id")
        if not dept_id:
            flash("Department authentication required. Please log in.", "warning")
            return redirect(url_for("department_login"))

        dept = db.get_department_by_id(dept_id)
        if not dept:
            session.clear()
            flash("Department record not found. Please log in again.", "danger")
            return redirect(url_for("department_login"))

        # Fetch fresh record from database
        is_allowed, status_code, message = evaluate_department_status(dept)
        if not is_allowed:
            session.clear()
            flash(message, "danger")
            return redirect(url_for("department_login"))

        # Attach department record to request
        request.current_department = dept
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator for Flask routes requiring Administrator authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_id = session.get("admin_id")
        if not admin_id:
            flash("Administrator login required.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function


def get_client_ip():
    """
    Helper to safely retrieve client IP address across proxied / serverless setups.
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'
