from flask import Flask, render_template, request, jsonify
import re
import os
import json
import base64
import urllib.request
import ssl
from werkzeug.utils import secure_filename
from botanical_pipeline import execute_plant_identification_pipeline

# =====================================================
# INITIALIZE FLASK & ENVIRONMENT CONFIGURATION
# =====================================================

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

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
# NOTE: Plant images are handled by plant_images.py
# Images are assigned by botanical_pipeline.py AFTER
# the final plant identity is validated from the dataset.
# NEVER use random image URLs or loremflickr here.
# =====================================================

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
        print("NVIDIA Vision AI Timeout / Exception:", e)
        return None

# =====================================================
# STRICT BOTANICAL TEXT AI PREDICTION ENGINE
# =====================================================

def query_nvidia_text_ai(user_input):
    if is_fake_or_invalid_plant_query(user_input):
        return {"Is_Plant": False, "Message": "The input text is invalid, fake, or does not describe botanical plant features."}

    prompt = f"""You are a Senior Botanical Classifier.
Analyze the user's input: "{user_input}"

CRITICAL RULE:
If the input describes non-plant objects (e.g., cars, laptops, electronics, clothes, random key mash like 'qwertyuiop', fake words, or non-botanical text):
You MUST respond strictly with:
{{
  "Is_Plant": false,
  "Message": "The input description does not appear to describe a plant species or botanical features."
}}

IF AND ONLY IF it describes a real plant, flower, tree, fruit, leaf, or medicinal herb:
Respond strictly with:
{{
  "Is_Plant": true,
  "Common_Name": "Exact Plant Name",
  "Scientific_Name": "Scientific Binomial Name",
  "Family": "Botanical Family",
  "Plant_Type": "Tree / Herb / Shrub / Flower",
  "Habitat": "Habitat & Growth Region",
  "Medicinal_Uses": "Medicinal uses",
  "Culinary_Uses": "Culinary uses",
  "Leaf_Shape": "Leaf Shape",
  "Flower_Color": "Flower Color",
  "Smell": "Aroma Profile",
  "Toxicity": "Toxicity Rating",
  "Ai_Explanation": "Detailed explanation of why this input matches the plant species."
}}
"""

    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 1024
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NVIDIA_API_KEY}"
    }

    try:
        req = urllib.request.Request(NVIDIA_BASE_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            content = res_json['choices'][0]['message']['content'].strip()
            
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            ai_dict = json.loads(content)
            if ai_dict.get("Is_Plant") is False:
                return {"Is_Plant": False, "Message": ai_dict.get("Message", "Input is not a plant description.")}

            # Database Cross-Validation & Zero-Hallucination Guardrail
            c_name_clean = clean_text(ai_dict.get("Common_Name", ""))
            s_name_clean = clean_text(ai_dict.get("Scientific_Name", ""))
            
            GENERIC_PLANT_STOPWORDS = {"plant", "tree", "leaf", "flower", "shrub", "herb", "fruit", "root", "species", "spp"}

            if df is not None:
                matched_row = None
                pred_c_words = {w for w in c_name_clean.split() if w not in GENERIC_PLANT_STOPWORDS and len(w) > 2}
                pred_s_words = {w for w in s_name_clean.split() if w not in GENERIC_PLANT_STOPWORDS and len(w) > 2}

                for idx, row in df.iterrows():
                    db_c = clean_text(row.get("Common_Name", ""))
                    db_s = clean_text(row.get("Scientific_Name", ""))
                    db_c_words = {w for w in db_c.split() if w not in GENERIC_PLANT_STOPWORDS and len(w) > 2}
                    db_s_words = {w for w in db_s.split() if w not in GENERIC_PLANT_STOPWORDS and len(w) > 2}

                    if (pred_c_words and db_c_words and pred_c_words == db_c_words) or \
                       (pred_s_words and db_s_words and pred_s_words == db_s_words) or \
                       (db_c and db_c == c_name_clean) or (db_s and db_s == s_name_clean):
                        matched_row = row
                        break

                    if pred_c_words and db_c_words and (pred_c_words.issubset(db_c_words) or db_c_words.issubset(pred_c_words)):
                        matched_row = row
                        break
                        
                if matched_row is not None:
                    ai_dict["Common_Name"] = str(matched_row.get("Common_Name", ai_dict.get("Common_Name")))
                    ai_dict["Scientific_Name"] = str(matched_row.get("Scientific_Name", ai_dict.get("Scientific_Name")))
                    ai_dict["Family"] = str(matched_row.get("Family", ai_dict.get("Family")))
                else:
                    return {"Is_Plant": False, "Message": "No matching plant species found in our botanical database."}

            ai_dict["Is_Plant"] = True
            
            return ai_dict
    except Exception as e:
        print("NVIDIA Text AI Exception:", e)
        return {"Is_Plant": False, "Message": "Text AI processing error."}

# =====================================================
# ROUTES
# =====================================================

@app.route("/", methods=["GET", "POST"])
def home():
    results = []
    user_text = ""
    uploaded_image_url = None
    not_plant_error = None
    candidates_debug = []

    try:
        if request.method == "POST":
            user_text = request.form.get("description", "").strip()
            file = request.files.get("plant_image")

            # QA Check 1: Empty Form Submission
            if (not file or file.filename == '') and not user_text:
                not_plant_error = "Please upload a plant photo or type/speak a plant description to begin identification."
                return render_template("index.html", results=[], user_text="", uploaded_image_url=None, not_plant_error=not_plant_error)

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
                        vision_result["Is_Verified_Image"] = False  # This is the uploaded photo itself
                        results.append(vision_result)
                    else:
                        # Vision AI failed — only run pipeline if user also provided a text description
                        if user_text:
                            pipeline_res = execute_plant_identification_pipeline(user_text)
                            if pipeline_res.get("is_plant"):
                                res_list = pipeline_res.get("results", [])
                                # Image from pipeline is already verified; also attach uploaded photo
                                for item in res_list:
                                    if not item.get("Photo_Url"):
                                        item["Photo_Url"] = uploaded_image_url
                                        item["Is_Verified_Image"] = False
                                results.extend(res_list)
                            else:
                                not_plant_error = pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")
                        else:
                            not_plant_error = "Vision AI could not identify the plant. Please add a text description to help identification."
                except Exception as ex:
                    print("File Upload QA Error:", ex)
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
                            # Photo_Url and Is_Verified_Image already set by pipeline
                            results.append(item)
                    else:
                        not_plant_error = pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")

        return render_template("index.html", results=results[:5], user_text=user_text, uploaded_image_url=uploaded_image_url, not_plant_error=not_plant_error, candidates_debug=candidates_debug)
    except Exception as general_ex:
        print("[ROUTE ERROR] Home route exception:", general_ex)
        return render_template("index.html", results=[], user_text=user_text, uploaded_image_url=None, not_plant_error="An error occurred while processing your request. Please try again.")


@app.route("/api/predict", methods=["POST"])
def api_predict():
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
                # No text and vision failed — cannot identify
                return jsonify({"is_plant": False, "status": "UNCERTAIN",
                                "error": "Please provide a text description to help identification."}), 200

        if text and len(results) < 5:
            if is_fake_or_invalid_plant_query(text):
                return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "The input text is invalid, fake, or does not describe botanical plant features."}), 200

            pipeline_res = execute_plant_identification_pipeline(text)
            if not pipeline_res.get("is_plant") and not results:
                return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": pipeline_res.get("message", "Plant identification is uncertain. Please provide more botanical characteristics.")}), 200
            
            if pipeline_res.get("is_plant"):
                for item in pipeline_res.get("results", []):
                    # Photo_Url and Is_Verified_Image already set by pipeline
                    results.append(item)

        if not results:
            return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "Plant identification is uncertain. Please provide more botanical characteristics."}), 200

        return jsonify({"is_plant": True, "query": text, "count": len(results), "results": results})
    except Exception as api_ex:
        print("[ROUTE ERROR] API Predict route exception:", api_ex)
        return jsonify({"is_plant": False, "status": "UNCERTAIN", "error": "Internal server processing error."}), 500


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)