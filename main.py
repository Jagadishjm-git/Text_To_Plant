from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import joblib
import re
import os
import json
import base64
import urllib.request
from werkzeug.utils import secure_filename
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# =====================================================
# INITIALIZE FLASK & LOAD LOCAL AI SYSTEM
# =====================================================

app = Flask(__name__)

# Upload configuration
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# NVIDIA API CONFIGURATION
NVIDIA_API_KEY = "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"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_TEXT_MODEL = "meta/llama-3.1-8b-instruct"
NVIDIA_VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

print("Loading local SentenceTransformer AI Model ('all-MiniLM-L6-v2')...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Loading dataset and precomputed embeddings...")
if os.path.exists("embeddings.pkl") and os.path.exists("data.pkl"):
    embeddings = joblib.load("embeddings.pkl")
    df = joblib.load("data.pkl")
    print(f"Local AI System Ready [OK] ({len(df)} plant entries indexed)")
else:
    print("WARNING: embeddings.pkl or data.pkl not found! Run train.py first.")
    embeddings = None
    df = None

# =====================================================
# CLEAN TEXT HELPER
# =====================================================

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# =====================================================
# PLANT PHOTO RESOLVER
# =====================================================

PLANT_PHOTO_MAP = {
    "pomegranate": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80",
    "aloe vera": "https://images.unsplash.com/photo-1596547609652-9cf5d8d76921?auto=format&fit=crop&w=600&q=80",
    "sunflower": "https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=600&q=80",
    "neem": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
    "neem tree": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
    "holy basil": "https://images.unsplash.com/photo-1618160702438-9b02ab6515c9?auto=format&fit=crop&w=600&q=80",
    "tulsi": "https://images.unsplash.com/photo-1618160702438-9b02ab6515c9?auto=format&fit=crop&w=600&q=80",
    "mango": "https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=600&q=80",
    "mango tree": "https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=600&q=80",
    "turmeric": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80",
    "banyan": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=600&q=80",
    "rose": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=600&q=80",
    "coconut": "https://images.unsplash.com/photo-1543637989-b59074092b15?auto=format&fit=crop&w=600&q=80"
}

def get_plant_photo(plant_name):
    clean_p = clean_text(plant_name)
    for key, url in PLANT_PHOTO_MAP.items():
        if key in clean_p or clean_p in key:
            return url
    return f"https://loremflickr.com/600/400/{clean_p.replace(' ', ',')},plant/all"

# =====================================================
# STRICT NVIDIA VISION AI IMAGE PREDICTION ENGINE
# =====================================================

def query_nvidia_vision_ai(image_b64, mime_type="image/jpeg", text_prompt=""):
    """
    Calls NVIDIA Vision AI NIM to strictly check if image contains a plant.
    If people/faces/non-plant objects are uploaded, returns Is_Plant: False.
    """
    prompt = f"""You are a Senior Botanical Vision AI Expert.
Examine this image carefully.

IF THE IMAGE CONTAINS A PLANT, FLOWER, LEAF, FRUIT, OR TREE:
Set "Is_Plant": true and identify the plant species (e.g., Pomegranate, Sunflower, Aloe Vera, Mango, Neem, Rose, etc.).
Respond strictly with valid JSON:
{{
  "Is_Plant": true,
  "Common_Name": "Identified Plant Name",
  "Scientific_Name": "Binomial Scientific Name",
  "Family": "Botanical Family",
  "Plant_Type": "Tree / Herb / Shrub / Flower",
  "Habitat": "Habitat & Growth Region",
  "Medicinal_Uses": "Medicinal uses",
  "Culinary_Uses": "Edible fruits / culinary uses",
  "Leaf_Shape": "Leaf Traits observed in photo",
  "Flower_Color": "Flower or Fruit color observed in photo",
  "Smell": "Aroma Profile",
  "Toxicity": "Low / Non-toxic",
  "Ai_Explanation": "2-3 sentences explaining why this photo matches the identified plant species."
}}

IF AND ONLY IF THE IMAGE CONTAINS NO PLANT, FLOWER, LEAF, FRUIT, OR TREE (e.g. photo of people, faces, animals, buildings, vehicles):
Respond strictly with valid JSON:
{{
  "Is_Plant": false,
  "Message": "No plant, flower, fruit, or leaf detected in this photo. The image appears to contain people, faces, or non-botanical objects. Please upload a clear photo of a plant species."
}}
"""

    payload = {
        "model": NVIDIA_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {NVIDIA_API_KEY}"
    }

    try:
        req = urllib.request.Request(NVIDIA_BASE_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            content = res_json['choices'][0]['message']['content'].strip()
            
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            ai_dict = json.loads(content)
            if ai_dict.get("Is_Plant") is False:
                return {"Is_Plant": False, "Message": ai_dict.get("Message", "No plant detected in this photo.")}
            
            ai_dict["Is_Plant"] = True
            ai_dict["Match_Percentage"] = 99
            ai_dict["Is_Nvidia_Ai"] = True
            ai_dict["Is_Vision_Ai"] = True
            return ai_dict
    except Exception as e:
        print("NVIDIA Vision AI Exception:", e)
        return None

# =====================================================
# STRICT NVIDIA TEXT AI PREDICTION ENGINE
# =====================================================

def query_nvidia_text_ai(user_input):
    prompt = f"""You are a Senior Botanical AI Classifier.
Analyze the user's input: "{user_input}"

First check if this describes a plant, flower, tree, fruit, leaf, or botanical medical herb.
If the input is non-botanical (e.g. describing cars, people, electronics, or random non-plant text):
Respond strictly with:
{{
  "Is_Plant": false,
  "Message": "The input description does not appear to describe a plant species or botanical features."
}}

If it DOES describe a plant:
Respond strictly with:
{{
  "Is_Plant": true,
  "Common_Name": "Plant Name",
  "Scientific_Name": "Scientific Binomial Name",
  "Family": "Botanical Family",
  "Plant_Type": "Type",
  "Habitat": "Habitat",
  "Medicinal_Uses": "Medicinal uses",
  "Culinary_Uses": "Culinary uses",
  "Leaf_Shape": "Leaf Shape",
  "Flower_Color": "Flower Color",
  "Smell": "Aroma Profile",
  "Toxicity": "Toxicity",
  "Ai_Explanation": "Detailed explanation of why this input matches the plant."
}}
"""

    payload = {
        "model": NVIDIA_TEXT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
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

            ai_dict["Is_Plant"] = True
            ai_dict["Match_Percentage"] = 99
            ai_dict["Is_Nvidia_Ai"] = True
            ai_dict["Photo_Url"] = get_plant_photo(ai_dict.get("Common_Name", ""))
            return ai_dict
    except Exception as e:
        print("NVIDIA Text AI Exception:", e)
        return None

# =====================================================
# LOCAL PREDICTION ENGINE WITH STRICT CONFIDENCE THRESHOLD
# =====================================================

def predict_plants_local(user_input, top_n=5, min_score_threshold=0.35):
    if embeddings is None or df is None:
        return []

    clean_input = clean_text(user_input)
    if not clean_input:
        return []

    input_embedding = model.encode([clean_input])
    similarities = cosine_similarity(input_embedding, embeddings)[0]
    scores = similarities.copy()

    input_words = set(clean_input.split())
    
    for i in range(len(df)):
        row = df.iloc[i]
        c_name = clean_text(row.get("Common_Name", ""))
        s_name = clean_text(row.get("Scientific_Name", ""))
        family = clean_text(row.get("Family", ""))
        med_use = clean_text(row.get("Medicinal_Uses_Description", ""))
        cul_use = clean_text(row.get("Culinary_Uses_Description", ""))
        
        boost = 0.0

        if c_name and c_name in clean_input:
            boost += 0.35
        elif any(w in c_name.split() for w in input_words if len(w) > 3):
            boost += 0.12

        if s_name and s_name in clean_input:
            boost += 0.35

        if family and family in clean_input:
            boost += 0.15

        for word in input_words:
            if len(word) > 3:
                if word in med_use:
                    boost += 0.03
                if word in cul_use:
                    boost += 0.03

        scores[i] += boost

    top_indices = scores.argsort()[::-1]
    
    results = []
    seen_names = set()

    for idx in top_indices:
        raw_score = scores[idx]
        
        if raw_score < min_score_threshold:
            break

        plant = df.iloc[idx]
        c_name = str(plant.get("Common_Name", "Unknown Plant")).strip()
        
        norm_name = c_name.lower()
        if norm_name in seen_names:
            continue
        seen_names.add(norm_name)

        s_name_norm = clean_text(plant.get("Scientific_Name", ""))
        
        if norm_name in clean_input or (s_name_norm and s_name_norm in clean_input):
            percentage = 99
        elif raw_score >= 0.95:
            percentage = 98
        elif raw_score >= 0.85:
            percentage = 96
        elif raw_score >= 0.75:
            percentage = 93
        elif raw_score >= 0.65:
            percentage = 89
        elif raw_score >= 0.50:
            percentage = 84
        elif raw_score >= 0.35:
            percentage = 78
        else:
            percentage = max(50, min(95, round(raw_score * 100)))

        res_item = {
            "Is_Plant": True,
            "Common_Name": c_name if c_name else "Unknown Plant",
            "Scientific_Name": str(plant.get("Scientific_Name", "N/A")).strip(),
            "Family": str(plant.get("Family", "N/A")).strip(),
            "Plant_Type": str(plant.get("Plant_Type", "N/A")).strip(),
            "Habitat": str(plant.get("Habitat_Description", "Not Specified")).strip(),
            "Medicinal_Uses": str(plant.get("Medicinal_Uses_Description", "Not Specified")).strip(),
            "Culinary_Uses": str(plant.get("Culinary_Uses_Description", "Not Specified")).strip(),
            "Industrial_Uses": str(plant.get("Industrial Use Description", "Not Specified")).strip(),
            "Leaf_Shape": str(plant.get("Leaf_Shape_Description", "Not Specified")).strip(),
            "Flower_Color": str(plant.get("Flower_Color_Description", "Not Specified")).strip(),
            "Smell": str(plant.get("Smell_Description", "Not Specified")).strip(),
            "Toxicity": str(plant.get("Toxicity_Level_Description", "Low")).strip(),
            "Match_Percentage": percentage,
            "Photo_Url": get_plant_photo(c_name)
        }
        
        results.append(res_item)
        if len(results) >= top_n:
            break

    return results

# =====================================================
# ROUTES
# =====================================================

@app.route("/", methods=["GET", "POST"])
def home():
    results = []
    user_text = ""
    uploaded_image_url = None
    not_plant_error = None

    if request.method == "POST":
        user_text = request.form.get("description", "").strip()
        file = request.files.get("plant_image")

        # 1. Handle Uploaded Image File with Strict Vision AI
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_image_url = f"/static/uploads/{filename}"

            with open(filepath, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode('utf-8')

            ext = filename.rsplit('.', 1)[1].lower()
            mime = f"image/{'jpeg' if ext in ['jpg', 'jpeg'] else ext}"
            
            vision_result = query_nvidia_vision_ai(b64_data, mime_type=mime, text_prompt=user_text)
            
            if vision_result and vision_result.get("Is_Plant") is False:
                not_plant_error = vision_result.get("Message", "No plant or botanical subject detected in this photo.")
            elif vision_result:
                vision_result["Photo_Url"] = uploaded_image_url
                results.append(vision_result)
                
                local_matches = predict_plants_local(vision_result.get("Common_Name", "") + " " + user_text, top_n=4)
                for loc in local_matches:
                    if loc.get("Common_Name", "").lower() != vision_result.get("Common_Name", "").lower():
                        results.append(loc)
        
        # 2. Text / Voice Input Only
        elif user_text:
            text_result = query_nvidia_text_ai(user_text)
            if text_result and text_result.get("Is_Plant") is False:
                not_plant_error = text_result.get("Message", "Input text does not describe a plant.")
            elif text_result:
                results.append(text_result)
                
                local_matches = predict_plants_local(user_text, top_n=5)
                if local_matches:
                    tv_name = text_result.get("Common_Name", "").lower()
                    for loc in local_matches:
                        if loc.get("Common_Name", "").lower() != tv_name:
                            results.append(loc)
            else:
                local_matches = predict_plants_local(user_text, top_n=5)
                if not local_matches:
                    not_plant_error = "No matching plant species found in our botanical database. Please refine your description."
                else:
                    results.extend(local_matches)

    return render_template("index.html", results=results[:5], user_text=user_text, uploaded_image_url=uploaded_image_url, not_plant_error=not_plant_error)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(silent=True) or {}
    text = data.get("description", "").strip()
    image_b64 = data.get("image_b64", "").strip()

    results = []
    
    if image_b64:
        mime = data.get("mime_type", "image/jpeg")
        vis_res = query_nvidia_vision_ai(image_b64, mime_type=mime, text_prompt=text)
        if vis_res and vis_res.get("Is_Plant") is False:
            return jsonify({"is_plant": False, "error": vis_res.get("Message")}), 200
        elif vis_res:
            results.append(vis_res)

    if text and len(results) < 5:
        text_res = query_nvidia_text_ai(text)
        if text_res and text_res.get("Is_Plant") is False and not results:
            return jsonify({"is_plant": False, "error": text_res.get("Message")}), 200
        elif text_res and text_res.get("Is_Plant"):
            results.append(text_res)
        
        local_res = predict_plants_local(text, top_n=5)
        for loc in local_res:
            if len(results) >= 5:
                break
            if not any(r.get("Common_Name", "").lower() == loc.get("Common_Name", "").lower() for r in results):
                results.append(loc)

    if not results:
        return jsonify({"is_plant": False, "error": "No matching plant species found."}), 200

    return jsonify({"is_plant": True, "query": text, "count": len(results), "results": results})


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)