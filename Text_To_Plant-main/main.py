from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import re
import os
import json
import base64
import urllib.request
import ssl
import datetime
import secrets
from werkzeug.utils import secure_filename

# Local modules
import db
from auth import (
    hash_password,
    verify_password,
    department_required,
    admin_required,
    evaluate_department_status,
    get_client_ip
)
from botanical_pipeline import execute_plant_identification_pipeline

# =====================================================
# INITIALIZE FLASK & ENVIRONMENT CONFIGURATION
# =====================================================

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Flask Session Security Secret
app.secret_key = os.environ.get("SESSION_SECRET", "plant_botanical_secure_session_secret_key_2026_xyz")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize database schema automatically on boot
try:
    db.init_database_tables()
except Exception as e:
    print(f"[DB INIT ERROR] Failed to initialize tables: {e}")

# Vercel Writable Directory handling
IS_VERCEL = os.environ.get('VERCEL') == '1' or 'VERCEL' in os.environ

if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp'
else:
    UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# AI API CONFIGURATION (ENV VARIABLE PRIORITY)
DEFAULT_NVIDIA_KEY = "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"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", DEFAULT_NVIDIA_KEY).strip()
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_TEXT_MODEL = "meta/llama-3.1-8b-instruct"
NVIDIA_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

# =====================================================
# CLEAN TEXT & FAKE WORD / GIBBERISH CHECKER
# =====================================================

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_gibberish_or_invalid(text):
    clean = clean_text(text)
    if not clean or len(clean) < 3:
        return True
    
    words = clean.split()
    letters = re.sub(r'[^a-z]', '', clean)
    if not letters:
        return True
        
    vowels = len(re.findall(r'[aeiou]', letters))
    vowel_ratio = vowels / len(letters)
    
    if len(letters) > 8 and (vowel_ratio < 0.12 or vowel_ratio > 0.85):
        return True
        
    known_gibberish = {"qwertyuiop", "asdfghjkl", "zxcvbnm", "test", "123456789", "abcd", "xyz"}
    if any(g in clean for g in known_gibberish) and not any(bot in clean for bot in ["plant", "tree", "leaf", "flower", "fruit", "herb", "root", "aloe", "rose"]):
        return True

    return False

FAKE_KEYWORD_PATTERNS = [
    r'\bmagic\b', r'\bunicorn\b', r'\bcyber\b', r'\bquantum\b', r'\btoy\b',
    r'\bartificial\b', r'\bplastic\b', r'\bblablabla\b', r'\bxyz\b', r'\bfake\b',
    r'\bnonexistent\b', r'\bdragon leaf\b', r'\bdragon plant\b', r'\bbattery\b',
    r'\bcharger\b', r'\blaptop\b', r'\bcar\b', r'\bvehicle\b', r'\bmotor\b'
]

def is_fake_or_invalid_plant_query(text):
    if is_gibberish_or_invalid(text):
        return True
    
    clean_p = clean_text(text)
    for pat in FAKE_KEYWORD_PATTERNS:
        if re.search(pat, clean_p):
            return True

    return False

# =====================================================
# STRICT BOTANICAL VISION AI PREDICTION ENGINE
# =====================================================

def query_nvidia_vision_ai(image_b64, mime_type="image/jpeg", text_prompt=""):
    if not NVIDIA_API_KEY:
        return None

    vision_system_instruction = (
        "You are an expert botanical computer vision model. "
        "Analyze the provided image and decide if it depicts a real plant, tree, flower, herb, leaf, fruit, or botanical organism. "
        "Respond strictly in valid JSON format with keys: "
        "\"Is_Plant\": boolean, \"Common_Name\": string or null, \"Scientific_Name\": string or null, "
        "\"Family\": string or null, \"Plant_Type\": string or null, \"Habitat\": string or null, "
        "\"Medicinal_Uses\": string or null, \"Culinary_Uses\": string or null, \"Industrial_Uses\": string or null, "
        "\"Leaf_Shape\": string or null, \"Flower_Color\": string or null, \"Smell\": string or null, "
        "\"Toxicity\": string or null, \"Match_Percentage\": integer 0-100, \"Ai_Explanation\": string, \"Message\": string or null."
    )

    prompt_content = f"User description provided with photo: '{text_prompt}'" if text_prompt else "Identify this plant from the photo."

    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "system",
                "content": vision_system_instruction
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_content},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 512,
        "response_format": {"type": "json_object"}
    }

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        ssl_ctx = ssl.create_default_context()
        req = urllib.request.Request(NVIDIA_BASE_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            content_text = res_json['choices'][0]['message']['content']
            
            content_text = re.sub(r'^```json\s*', '', content_text.strip())
            content_text = re.sub(r'\s*```$', '', content_text.strip())

            result_dict = json.loads(content_text)
            
            if result_dict.get("Is_Plant") is True:
                result_dict["Is_Vision_Ai"] = True
                if not result_dict.get("Match_Percentage"):
                    result_dict["Match_Percentage"] = 95
            return result_dict
    except Exception as e:
        print("NVIDIA Vision AI Exception:", e)
        return None

# =====================================================
# PUBLIC & AUTHENTICATION ROUTES
# =====================================================

@app.route("/", methods=["GET"])
def landing():
    """
    Public Landing Page.
    Introduces the Institutional Multimodal Botanical Intelligence platform.
    If department is already logged in, redirects directly to /dashboard.
    """
    if session.get("department_id"):
        return redirect(url_for("department_dashboard"))
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    return render_template("landing.html")


@app.route("/login", methods=["GET", "POST"])
def department_login():
    """
    Department Login Route.
    Accepts ONLY: Department ID/Code and Password.
    No student signup or social logins allowed.
    """
    if session.get("department_id"):
        return redirect(url_for("department_dashboard"))

    error = None
    message = None
    department_code = ""

    if request.method == "POST":
        department_code = request.form.get("department_code", "").strip().upper()
        password = request.form.get("password", "").strip()

        if not department_code or not password:
            error = "Please enter both Department Code and Password."
            return render_template("login.html", error=error, department_code=department_code)

        dept = db.get_department_by_code(department_code)
        if not dept or not verify_password(password, dept["password_hash"]):
            error = "Invalid Department ID or Password. Please verify your credentials."
            db.record_audit_log(f"Failed login attempt for department code '{department_code}'", ip_address=get_client_ip())
            return render_template("login.html", error=error, department_code=department_code)

        # Check Department Status & Subscription
        is_allowed, status_code, status_msg = evaluate_department_status(dept)
        if not is_allowed:
            db.record_audit_log(f"Login blocked for {department_code} (Status: {status_code})", department_id=dept["id"], department_code=department_code, ip_address=get_client_ip())
            return render_template("login.html", error=status_msg, department_code=department_code)

        # Login Successful
        session["department_id"] = dept["id"]
        session["department_code"] = dept["department_code"]
        session["department_name"] = dept["department_name"]
        session["institution_name"] = dept["institution_name"]

        db.update_department_last_login(dept["id"])
        db.record_audit_log(f"{dept['department_code']} logged in", department_id=dept["id"], department_code=dept["department_code"], ip_address=get_client_ip())

        next_page = request.args.get("next") or url_for("department_dashboard")
        return redirect(next_page)

    return render_template("login.html", error=error, message=message, department_code=department_code)


@app.route("/logout", methods=["GET"])
def department_logout():
    """Logs out the department account and clears session."""
    dept_code = session.get("department_code")
    dept_id = session.get("department_id")
    if dept_code:
        db.record_audit_log(f"{dept_code} logged out", department_id=dept_id, department_code=dept_code, ip_address=get_client_ip())

    session.pop("department_id", None)
    session.pop("department_code", None)
    session.pop("department_name", None)
    session.pop("institution_name", None)
    return redirect(url_for("department_login"))


# =====================================================
# DEPARTMENT PROTECTED PORTAL (PLANT IDENTIFICATION)
# =====================================================

@app.route("/dashboard", methods=["GET", "POST"])
@app.route("/plant-identification", methods=["GET", "POST"])
@department_required
def department_dashboard():
    """
    Protected Department Plant Identification Portal.
    Allows image upload, text descriptions, and voice input.
    Preserves all existing botanical pipeline functionality.
    """
    results = []
    user_text = ""
    uploaded_image_url = None
    not_plant_error = None
    candidates_debug = []
    current_dept = getattr(request, 'current_department', None) or db.get_department_by_id(session.get("department_id"))

    try:
        if request.method == "POST":
            user_text = request.form.get("description", "").strip()
            file = request.files.get("plant_image")

            if (not file or file.filename == '') and not user_text:
                not_plant_error = "Please upload a plant photo or type/speak a plant description to begin identification."
                return render_template("index.html", results=[], user_text="", uploaded_image_url=None, not_plant_error=not_plant_error, current_dept=current_dept)

            # 1. Handle Uploaded Image File with Vision AI
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    file.save(filepath)

                    with open(filepath, "rb") as img_f:
                        b64_data = base64.b64encode(img_f.read()).decode('utf-8')

                    ext = filename.rsplit('.', 1)[1].lower()
                    mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
                    uploaded_image_url = f"data:{mime};base64,{b64_data}"
                    
                    vision_result = query_nvidia_vision_ai(b64_data, mime_type=mime, text_prompt=user_text)
                    
                    if vision_result and vision_result.get("Is_Plant") is False:
                        not_plant_error = vision_result.get("Message", "No plant or botanical subject detected in this photo.")
                    elif vision_result:
                        vision_result["Photo_Url"] = uploaded_image_url
                        vision_result["Is_Verified_Image"] = False
                        results.append(vision_result)
                        # Record audit log
                        db.record_audit_log(f"{current_dept['department_code']} identified {vision_result.get('Common_Name', 'Plant')} via photo upload", department_id=current_dept["id"], department_code=current_dept["department_code"], ip_address=get_client_ip())
                    else:
                        if user_text:
                            pipeline_res = execute_plant_identification_pipeline(user_text)
                            if pipeline_res.get("is_plant"):
                                res_list = pipeline_res.get("results", [])
                                for item in res_list:
                                    if not item.get("Photo_Url"):
                                        item["Photo_Url"] = uploaded_image_url
                                        item["Is_Verified_Image"] = False
                                results.extend(res_list)
                                if results:
                                    db.record_audit_log(f"{current_dept['department_code']} identified {results[0].get('Common_Name')} via multimodal input", department_id=current_dept["id"], department_code=current_dept["department_code"], ip_address=get_client_ip())
                            else:
                                not_plant_error = pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")
                        else:
                            not_plant_error = "Vision AI could not identify the plant. Please add a text description to help identification."
                except Exception as ex:
                    print("File Upload Error:", ex)
                    not_plant_error = "Unable to process uploaded image file. Please try a different image format (JPG/PNG)."
            
            # 2. Text / Voice Input Only (Dataset-First Pipeline)
            elif user_text:
                if is_fake_or_invalid_plant_query(user_text):
                    not_plant_error = "The input text is invalid, fake, or does not describe botanical plant features."
                else:
                    pipeline_res = execute_plant_identification_pipeline(user_text)
                    candidates_debug = pipeline_res.get("candidates_debug", [])
                    
                    if pipeline_res.get("is_plant") and pipeline_res.get("results"):
                        for item in pipeline_res["results"]:
                            results.append(item)
                        # Record audit log
                        first_match = results[0].get("Common_Name") if results else "Plant"
                        db.record_audit_log(f"{current_dept['department_code']} identified {first_match}", department_id=current_dept["id"], department_code=current_dept["department_code"], ip_address=get_client_ip())
                    else:
                        not_plant_error = pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")

        return render_template("index.html", results=results[:5], user_text=user_text, uploaded_image_url=uploaded_image_url, not_plant_error=not_plant_error, candidates_debug=candidates_debug, current_dept=current_dept)
    except Exception as general_ex:
        print("[ROUTE ERROR] Dashboard route exception:", general_ex)
        return render_template("index.html", results=[], user_text=user_text, uploaded_image_url=None, not_plant_error="An error occurred while processing your request. Please try again.", current_dept=current_dept)


# =====================================================
# PROTECTED API PREDICT ENDPOINT
# =====================================================

@app.route("/api/predict", methods=["POST"])
def api_predict():
    """
    Protected REST API Endpoint for Plant Identification.
    Requires an active, non-expired department session or Bearer department auth.
    """
    # 1. Authentication Check
    dept_id = session.get("department_id")
    dept_code_header = request.headers.get("X-Department-Code")
    auth_header = request.headers.get("Authorization")

    department = None
    if dept_id:
        department = db.get_department_by_id(dept_id)
    elif dept_code_header:
        department = db.get_department_by_code(dept_code_header)
    elif auth_header and auth_header.startswith("Bearer "):
        token_code = auth_header.replace("Bearer ", "").strip()
        department = db.get_department_by_code(token_code)

    if not department:
        return jsonify({
            "is_plant": False,
            "error": "Authentication required. Valid department login or token required."
        }), 401

    # 2. Status & Subscription Validation
    is_allowed, status_code, message = evaluate_department_status(department)
    if not is_allowed:
        return jsonify({
            "is_plant": False,
            "error": message,
            "status": status_code
        }), 403

    # 3. Process Prediction Request
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("description", "").strip()
        image_b64 = data.get("image_b64", "").strip()

        if not text and not image_b64:
            return jsonify({"is_plant": False, "error": "Please provide an image_b64 or description parameter."}), 400

        results = []
        
        if image_b64:
            mime = data.get("mime_type", "image/jpeg")
            vis_res = query_nvidia_vision_ai(image_b64, mime_type=mime, text_prompt=text)
            if vis_res and vis_res.get("Is_Plant") is False:
                return jsonify({"is_plant": False, "error": vis_res.get("Message")}), 200
            elif vis_res and vis_res.get("Common_Name"):
                text = vis_res.get("Common_Name")
                results.append(vis_res)
            elif not text:
                return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "Please provide a text description to help identification."}), 200

        if text and len(results) < 5:
            if is_fake_or_invalid_plant_query(text):
                return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "The input text is invalid, fake, or does not describe botanical plant features."}), 200

            pipeline_res = execute_plant_identification_pipeline(text)
            if not pipeline_res.get("is_plant") and not results:
                return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")}), 200
            
            if pipeline_res.get("is_plant"):
                for item in pipeline_res.get("results", []):
                    results.append(item)

        if not results:
            return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "Plant identification is uncertain. Please provide more botanical characteristics."}), 200

        # Audit log successful prediction
        first_c_name = results[0].get("Common_Name") if results else "Plant"
        db.record_audit_log(f"{department['department_code']} identified {first_c_name} via API", department_id=department["id"], department_code=department["department_code"], ip_address=get_client_ip())

        return jsonify({"is_plant": True, "query": text, "count": len(results), "results": results})
    except Exception as api_ex:
        print("[API ERROR] Predict route exception:", api_ex)
        return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "Internal server processing error."}), 500


# =====================================================
# PAYMENT & SUBSCRIPTION GATEWAY ROUTES
# =====================================================

@app.route("/payment/<payment_reference>", methods=["GET"])
def payment_invoice_page(payment_reference):
    """
    Renders payment invoice and verification portal for department activation/renewal.
    """
    payment = db.get_payment_by_reference(payment_reference)
    if not payment:
        return "Payment reference not found.", 404
    
    department = db.get_department_by_id(payment["department_id"])
    if not department:
        return "Associated department not found.", 404

    return render_template("payment.html", payment=payment, department=department)


@app.route("/api/payment/verify", methods=["POST"])
def verify_payment_api():
    """
    Server-side Payment Verification Endpoint.
    Validates payment reference, marks payment PAID, and activates department access.
    """
    payment_ref = request.form.get("payment_reference") or (request.get_json(silent=True) or {}).get("payment_reference")
    gateway_ref = request.form.get("gateway_ref") or (request.get_json(silent=True) or {}).get("gateway_ref")
    redirect_to = request.form.get("redirect_to")

    if not payment_ref:
        if redirect_to:
            flash("Missing payment reference.", "error")
            return redirect(redirect_to)
        return jsonify({"success": False, "error": "Missing payment_reference parameter."}), 400

    payment = db.get_payment_by_reference(payment_ref)
    if not payment:
        if redirect_to:
            flash("Invalid payment reference.", "error")
            return redirect(redirect_to)
        return jsonify({"success": False, "error": "Payment record not found."}), 404

    # Determine duration
    dept = db.get_department_by_id(payment["department_id"])
    duration_months = 12
    if dept and dept.get("subscription_plan"):
        plan_name = dept["subscription_plan"]
        if "1 Month" in plan_name: duration_months = 1
        elif "3 Month" in plan_name: duration_months = 3
        elif "6 Month" in plan_name: duration_months = 6
        elif "12 Month" in plan_name: duration_months = 12

    success, msg = db.mark_payment_verified(payment_ref, gateway_reference=gateway_ref or "GATEWAY_VERIFIED_SUCCESS", duration_months=duration_months)
    
    if success and dept:
        db.record_audit_log(f"{dept['department_code']} payment of ₹{payment['amount']} verified. Account activated for {duration_months} months.", department_id=dept["id"], department_code=dept["department_code"], ip_address=get_client_ip())

    if redirect_to:
        return redirect(redirect_to)

    return jsonify({"success": success, "message": msg})


# =====================================================
# ADMINISTRATOR CONSOLE ROUTES
# =====================================================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """
    Administrator Authentication Route.
    Separate from Department login.
    """
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))

    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()

        admin = db.get_admin_by_username(username)
        if not admin or not verify_password(password, admin["password_hash"]):
            error = "Invalid administrator credentials."
            db.record_audit_log(f"Failed admin login attempt for username '{username}'", ip_address=get_client_ip())
            return render_template("admin_login.html", error=error, username=username)

        # Admin login success
        session["admin_id"] = admin["id"]
        session["admin_username"] = admin["username"]
        db.update_admin_last_login(admin["id"])
        db.record_audit_log(f"Administrator '{admin['username']}' logged in", ip_address=get_client_ip())

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html", error=error, username=username)


@app.route("/admin/logout", methods=["GET"])
def admin_logout():
    """Administrator Logout."""
    admin_user = session.get("admin_username")
    if admin_user:
        db.record_audit_log(f"Administrator '{admin_user}' logged out", ip_address=get_client_ip())

    session.pop("admin_id", None)
    session.pop("admin_username", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    """
    Administrator Console Dashboard.
    Displays metrics, department accounts, payments, audit logs, and subscription tiers.
    """
    metrics = db.get_dashboard_metrics()
    departments = db.get_all_departments()
    payments = db.get_all_payments()
    audit_logs = db.get_recent_audit_logs(limit=60)
    subscription_plans = db.get_all_subscription_plans()

    return render_template(
        "admin_dashboard.html",
        metrics=metrics,
        departments=departments,
        payments=payments,
        audit_logs=audit_logs,
        subscription_plans=subscription_plans
    )


@app.route("/admin/departments/create", methods=["POST"])
@admin_required
def admin_create_department():
    """
    Workflow Step: Admin creates department account.
    Account initially receives PENDING status.
    Generates payment invoice request.
    """
    dept_name = request.form.get("department_name", "").strip()
    dept_code = request.form.get("department_code", "").strip().upper()
    inst_name = request.form.get("institution_name", "").strip()
    email = request.form.get("contact_email", "").strip().lower()
    sub_plan = request.form.get("subscription_plan", "12 Months")
    password = request.form.get("password", "").strip() or "Dept@Pass2026!"

    if not dept_name or not dept_code or not inst_name or not email:
        flash("All fields are required to register a department.", "error")
        return redirect(url_for("admin_dashboard"))

    existing = db.get_department_by_code(dept_code)
    if existing:
        flash(f"Department code '{dept_code}' already exists. Please choose a unique code.", "error")
        return redirect(url_for("admin_dashboard"))

    # Determine pricing from subscription plan
    amount = 5000.0
    duration_months = 12
    if "1 Month" in sub_plan:
        amount = 1000.0
        duration_months = 1
    elif "3 Month" in sub_plan:
        amount = 2500.0
        duration_months = 3
    elif "6 Month" in sub_plan:
        amount = 4000.0
        duration_months = 6
    elif "12 Month" in sub_plan or "Annual" in sub_plan:
        amount = 5000.0
        duration_months = 12

    pwd_hash = hash_password(password)
    dept_id = db.create_department(
        department_name=dept_name,
        department_code=dept_code,
        institution_name=inst_name,
        contact_email=email,
        password_hash=pwd_hash,
        subscription_plan=sub_plan
    )

    # Generate payment reference code
    pay_ref = f"PAY-{dept_code}-{secrets.token_hex(4).upper()}"
    db.create_payment_record(
        department_id=dept_id,
        payment_reference=pay_ref,
        amount=amount,
        currency="INR",
        duration_months=duration_months,
        notes=f"Initial Subscription Payment for {sub_plan}"
    )

    db.record_audit_log(f"Admin created department {dept_code} (Status: PENDING). Payment invoice {pay_ref} generated.", department_id=dept_id, department_code=dept_code, ip_address=get_client_ip())

    flash(f"Department '{dept_code}' created successfully (Status: PENDING). Payment invoice: {pay_ref}", "message")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/departments/<int:department_id>/status", methods=["POST"])
@admin_required
def admin_update_department_status(department_id):
    """Admin toggles status: ACTIVE, SUSPENDED, EXPIRED."""
    new_status = request.form.get("status", "ACTIVE").strip().upper()
    dept = db.get_department_by_id(department_id)
    if not dept:
        flash("Department not found.", "error")
        return redirect(url_for("admin_dashboard"))

    if new_status == "ACTIVE":
        # If department was never activated or is expired, activate for 12 months
        if not dept.get("subscription_end") or dept.get("status") == "EXPIRED":
            db.activate_department_subscription(department_id, duration_months=12)
        else:
            db.update_department_status(department_id, status="ACTIVE", subscription_status="ACTIVE")
    elif new_status == "SUSPENDED":
        db.update_department_status(department_id, status="SUSPENDED", subscription_status="SUSPENDED")
    elif new_status == "EXPIRED":
        db.update_department_status(department_id, status="EXPIRED", subscription_status="EXPIRED")

    db.record_audit_log(f"Admin updated {dept['department_code']} status to {new_status}", department_id=department_id, department_code=dept['department_code'], ip_address=get_client_ip())
    flash(f"Department {dept['department_code']} status updated to {new_status}.", "message")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/departments/<int:department_id>/renew", methods=["POST"])
@admin_required
def admin_renew_department(department_id):
    """Admin renews or extends a department's subscription."""
    months = int(request.form.get("duration_months", 12))
    dept = db.get_department_by_id(department_id)
    if not dept:
        flash("Department not found.", "error")
        return redirect(url_for("admin_dashboard"))

    amount = months * 450.0  # e.g. calculated renewal amount
    pay_ref = f"REN-{dept['department_code']}-{secrets.token_hex(4).upper()}"
    
    # Create payment record
    db.create_payment_record(
        department_id=department_id,
        payment_reference=pay_ref,
        amount=amount,
        currency="INR",
        duration_months=months,
        notes=f"Subscription Renewal (+{months} Months)"
    )

    # Mark verified
    db.mark_payment_verified(pay_ref, gateway_reference="ADMIN_MANUAL_RENEWAL", duration_months=months)

    db.record_audit_log(f"{dept['department_code']} subscription renewed for +{months} months by Admin", department_id=department_id, department_code=dept['department_code'], ip_address=get_client_ip())
    flash(f"Subscription for {dept['department_code']} extended by {months} months.", "message")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/departments/<int:department_id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(department_id):
    """Admin resets department password."""
    new_pwd = request.form.get("new_password", "").strip()
    dept = db.get_department_by_id(department_id)
    if not dept or not new_pwd:
        flash("Department or new password invalid.", "error")
        return redirect(url_for("admin_dashboard"))

    db.update_department_password(department_id, hash_password(new_pwd))
    db.record_audit_log(f"Admin reset password for {dept['department_code']}", department_id=department_id, department_code=dept['department_code'], ip_address=get_client_ip())
    flash(f"Password for {dept['department_code']} reset successfully.", "message")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/departments/<int:department_id>/delete", methods=["POST"])
@admin_required
def admin_delete_department(department_id):
    """Admin deletes department record and history."""
    dept = db.get_department_by_id(department_id)
    if dept:
        dept_code = dept["department_code"]
        db.delete_department(department_id)
        db.record_audit_log(f"Admin deleted department {dept_code}", ip_address=get_client_ip())
        flash(f"Department {dept_code} has been deleted.", "message")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/payments/<payment_reference>/verify", methods=["POST"])
@admin_required
def admin_verify_payment(payment_reference):
    """Admin manually verifies a pending payment and activates department access."""
    success, msg = db.mark_payment_verified(payment_reference, gateway_reference="ADMIN_DIRECT_VERIFY")
    if success:
        flash(f"Payment {payment_reference} verified and department activated.", "message")
    else:
        flash(f"Payment verification failed: {msg}", "error")
    return redirect(url_for("admin_dashboard"))


# =====================================================
# RUN APPLICATION
# =====================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)