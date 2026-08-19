"""
auth.py
Authentication, Session Protection Middleware, and Subscription Validation for Department Portal.
"""

from functools import wraps
import datetime
from flask import session, request, redirect, url_for, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
import db

def hash_password(password: str) -> str:
    """Securely hash a plain text password using Werkzeug's PBKDF2/Scrypt implementation."""
    return generate_password_hash(password.strip(), method="pbkdf2:sha256", salt_length=16)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored secure hash."""
    if not plain_password or not hashed_password:
        return False
    return check_password_hash(hashed_password, plain_password.strip())


def get_client_ip():
    """Extract client IP address from Flask request headers."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


def evaluate_department_status(department):
    """
    Evaluates department account status and real-time subscription validity.
    Returns (is_allowed: bool, status: str, message: str).
    """
    if not department:
        return False, "NOT_FOUND", "Department record not found."
    
    current_status = str(department.get("status", "")).upper()
    
    if current_status == "PENDING":
        return False, "PENDING", "Your department account is awaiting activation. Please complete payment or contact the administrator."
    
    if current_status == "SUSPENDED":
        return False, "SUSPENDED", "Your department access has been suspended. Please contact the administrator."
    
    # Check subscription expiration
    sub_end = department.get("subscription_end")
    if sub_end:
        try:
            # Parse datetime string from db
            sub_end_dt = datetime.datetime.fromisoformat(str(sub_end).replace("Z", "+00:00"))
            if sub_end_dt.tzinfo is None:
                sub_end_dt = sub_end_dt.replace(tzinfo=datetime.timezone.utc)
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            
            if now_dt > sub_end_dt:
                # Dynamically update department to EXPIRED in database
                db.update_department_status(department["id"], status="EXPIRED", subscription_status="EXPIRED")
                return False, "EXPIRED", "Your department subscription has expired. Please renew to continue."
        except Exception as e:
            print(f"[AUTH DATE PARSE ERROR] {e}")

    if current_status == "EXPIRED":
        return False, "EXPIRED", "Your department subscription has expired. Please renew to continue."

    if current_status == "ACTIVE":
        return True, "ACTIVE", "Active"

    return False, "INACTIVE", f"Account access unavailable (Status: {current_status})."


def department_required(f):
    """
    Decorator for routes accessible only by authenticated ACTIVE departments with valid subscription.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        dept_id = session.get("department_id")
        if not dept_id:
            # If API request, return JSON 401
            if request.path.startswith("/api/"):
                return jsonify({
                    "is_plant": False,
                    "error": "Authentication required. Please log in with your Department credentials."
                }), 401
            return redirect(url_for("department_login", next=request.path))

        # Fetch fresh record from database
        department = db.get_department_by_id(dept_id)
        if not department:
            session.pop("department_id", None)
            session.pop("department_code", None)
            session.pop("department_name", None)
            if request.path.startswith("/api/"):
                return jsonify({"is_plant": False, "error": "Department account does not exist."}), 401
            return redirect(url_for("department_login"))

        is_allowed, status_code, message = evaluate_department_status(department)
        if not is_allowed:
            if request.path.startswith("/api/"):
                return jsonify({"is_plant": False, "error": message, "status": status_code}), 403
            return render_template("login.html", error=message, department_code=department.get("department_code"))

        # Attach fresh department object to request context
        request.current_department = department
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator for routes accessible only by authenticated Administrators.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_id = session.get("admin_id")
        if not admin_id:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Admin authentication required."}), 401
            return redirect(url_for("admin_login", next=request.path))

        request.admin_username = session.get("admin_username")
        return f(*args, **kwargs)
    return decorated_function
