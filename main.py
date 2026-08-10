from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import joblib
import re
import os
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# =====================================================
# INITIALIZE FLASK & LOAD AI SYSTEM
# =====================================================

app = Flask(__name__)

print("Loading AI Model ('all-MiniLM-L6-v2')...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Loading dataset and embeddings...")
if os.path.exists("embeddings.pkl") and os.path.exists("data.pkl"):
    embeddings = joblib.load("embeddings.pkl")
    df = joblib.load("data.pkl")
    print(f"AI System Ready [OK] ({len(df)} plant entries indexed)")
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
# PREDICTION ENGINE
# =====================================================

def predict_plants(user_input, top_n=5):
    if embeddings is None or df is None:
        return []

    clean_input = clean_text(user_input)
    if not clean_input:
        return []

    # 1. Compute Semantic Vector Embedding
    input_embedding = model.encode([clean_input])

    # 2. Cosine Similarity against indexed dataset
    similarities = cosine_similarity(input_embedding, embeddings)[0]
    scores = similarities.copy()

    # 3. Dynamic Name & Characteristic Keyword Boosting
    input_words = set(clean_input.split())
    
    for i in range(len(df)):
        row = df.iloc[i]
        c_name = clean_text(row.get("Common_Name", ""))
        s_name = clean_text(row.get("Scientific_Name", ""))
        family = clean_text(row.get("Family", ""))
        med_use = clean_text(row.get("Medicinal_Uses_Description", ""))
        cul_use = clean_text(row.get("Culinary_Uses_Description", ""))
        
        boost = 0.0

        # Exact or partial common name match
        if c_name and c_name in clean_input:
            boost += 0.35
        elif any(w in c_name.split() for w in input_words if len(w) > 3):
            boost += 0.12

        # Scientific name match
        if s_name and s_name in clean_input:
            boost += 0.35

        # Family match
        if family and family in clean_input:
            boost += 0.15

        # Key usage word matches
        for word in input_words:
            if len(word) > 3:
                if word in med_use:
                    boost += 0.03
                if word in cul_use:
                    boost += 0.03

        scores[i] += boost

    # 4. Get Top N unique plants
    top_indices = scores.argsort()[::-1]
    
    results = []
    seen_names = set()

    for idx in top_indices:
        plant = df.iloc[idx]
        c_name = str(plant.get("Common_Name", "Unknown Plant")).strip()
        
        # Deduplicate identical species names in result list
        norm_name = c_name.lower()
        if norm_name in seen_names:
            continue
        seen_names.add(norm_name)

        raw_score = scores[idx]

        # Calculate user-friendly confidence percentage
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
            "Match_Percentage": percentage
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

    if request.method == "POST":
        user_text = request.form.get("description", "").strip()
        if user_text:
            results = predict_plants(user_text, top_n=5)

    return render_template("index.html", results=results, user_text=user_text)


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(silent=True) or {}
    text = data.get("description", "").strip()
    if not text:
        return jsonify({"error": "Please provide a 'description' parameter."}), 400

    results = predict_plants(text, top_n=5)
    return jsonify({"query": text, "count": len(results), "results": results})


# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)