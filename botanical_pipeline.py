import os
import sys
import re
import csv
import json
import urllib.request
import ssl

# Disable SSL verification for external botanical API calls if required
ssl_ctx = ssl._create_unverified_context()

def find_plants_csv():
    candidates = [
        os.path.join(os.path.dirname(__file__), 'plants.csv'),
        os.path.join(os.path.dirname(__file__), '..', 'plants.csv'),
        os.path.join(os.getcwd(), 'plants.csv'),
        '/var/task/plants.csv'
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(os.path.dirname(__file__), 'plants.csv')

PLANTS_CSV_PATH = find_plants_csv()

# =====================================================
# 1. BOTANICAL KNOWLEDGE BASE & FEATURE LEXICON
# =====================================================

GENERIC_BOTANICAL_STOPWORDS = {
    "plant", "tree", "leaf", "leaves", "flower", "flowers", "fruit", "fruits", 
    "root", "roots", "stem", "stems", "herb", "herbs", "shrub", "shrubs",
    "species", "spp", "area", "found", "looking", "identify", "used", "uses",
    "green", "white", "yellow", "tropical", "subtropical", "medicinal", "growing",
    "grown", "native", "common", "found", "area", "type", "description", "properties"
}

DISTINCTIVE_BOTANICAL_MARKERS = {
    "drip tip": 0.40,
    "cordate": 0.35,
    "syconium": 0.45,
    "rhizome": 0.35,
    "prop root": 0.40,
    "aerial root": 0.40,
    "needle-like": 0.40,
    "spiny": 0.30,
    "palmate-lobed": 0.35,
    "star-shaped": 0.35,
    "compound tripinnate": 0.40,
    "compound pinnate": 0.30,
    "raceme": 0.30,
    "spadix": 0.40,
    "pseudostem": 0.35,
    "jointed culm": 0.40,
    "woody culm": 0.40,
    "bell-shaped": 0.30,
    "orbicular": 0.35,
    "floating": 0.35,
    "gel": 0.35,
    "succulent": 0.35,
    "serrated": 0.30,
    "aromatic": 0.30
}

FLOWER_COLOR_KEYWORDS = {"crimson", "yellow", "white", "purple", "pink", "orange-red", "red", "greenish", "yellow-green", "pale yellow", "black", "brown"}
LEAF_SHAPE_KEYWORDS = {"lanceolate", "ovate", "cordate", "elliptic", "linear", "orbicular", "palmate-lobed", "star-shaped", "oblong", "needle-like", "spiny-lobed"}
LEAF_ARRANGEMENT_KEYWORDS = {"opposite", "alternate", "rosette", "spiral", "floating"}
LEAF_TYPE_KEYWORDS = {"simple", "compound pinnate", "compound tripinnate", "palmate", "succulent"}
FLOWER_TYPE_KEYWORDS = {"panicle", "spike", "syconium", "solitary", "spikelet", "raceme", "fascicle", "bell-shaped", "corymb", "spadix"}
FRUIT_TYPE_KEYWORDS = {"drupe", "berry", "capsule", "achene", "syconium fig", "grain", "aggregate", "capsule pod", "capsule boll"}
STEM_ROOT_KEYWORDS = {"woody", "herbaceous", "pseudostem", "rhizome", "taproot", "prop roots", "aerial roots", "fibrous", "adventitious", "jointed culm"}
PLANT_TYPE_KEYWORDS = {"tree", "herb", "shrub", "grass", "climber", "palm tree", "succulent herb", "aquatic herb", "cactus", "moss"}
HABITAT_KEYWORDS = {"tropical", "subtropical", "dry forests", "rainforests", "wetlands", "marshes", "ponds", "lakes", "coastal", "arid", "villages", "gardens"}
MEDICINAL_USE_KEYWORDS = {"dental pain", "respiratory", "fever", "stress", "skin diseases", "diabetes", "digestive", "anti-inflammatory", "vitamin c", "adaptogen", "wound healing", "memory", "antioxidant", "analgesic", "antiseptic", "potassium", "skin healing", "burns", "laxative"}

# =====================================================
# 2. DATASET ENGINE
# =====================================================

class DatasetEngine:
    def __init__(self, csv_path=PLANTS_CSV_PATH):
        self.csv_path = csv_path
        self.plants = []
        self.plant_map = {}
        self.load_dataset()

    def load_dataset(self):
        if not os.path.exists(self.csv_path):
            print(f"[ERROR] Dataset file not found at: {self.csv_path}")
            return

        seen_keys = set()
        cleaned_records = []

        with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_name = str(row.get('Common_Name', '')).strip()
                s_name = str(row.get('Scientific_Name', '')).strip()
                if not c_name or not s_name:
                    continue

                dedup_key = (c_name.lower(), s_name.lower())
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                # Create comprehensive normalized search document combining all 28+ fields
                doc_parts = [
                    c_name, s_name,
                    row.get('Family', ''), row.get('Kingdom', ''), row.get('Class', ''), row.get('Order', ''),
                    row.get('Plant_Type', ''), row.get('Life_Span', ''),
                    row.get('Leaf_Type_Description', ''), row.get('Leaf_Arrangement_Description', ''), row.get('Leaf_Shape_Description', ''),
                    row.get('Stem_Type_Description', ''), row.get('Stem_Texture_Description', ''),
                    row.get('Flower_Color_Description', ''), row.get('Flower_Type_Description', ''), row.get('Flowering_Season', ''),
                    row.get('Fruit_Type_Description', ''), row.get('Fruit_Color_Description', ''),
                    row.get('Root_Type_Description', ''), row.get('Habitat_Description', ''), row.get('Native_Region_India', ''),
                    row.get('Medicinal_Uses_Description', ''), row.get('Culinary_Uses_Description', ''), row.get('Industrial Use Description', ''),
                    row.get('Toxicity_Level_Description', ''), row.get('Smell_Description', ''), row.get('Text Input', '')
                ]
                doc_text = " ".join([str(p) for p in doc_parts if p]).lower()
                row['search_doc'] = doc_text
                row['search_words'] = set(doc_text.split())
                cleaned_records.append(row)
                self.plant_map[c_name.lower()] = row

        self.plants = cleaned_records
        print(f"[DatasetEngine] Lightweight initialization complete. Loaded {len(self.plants)} records.")

    def get_plant_by_name(self, common_name):
        if not common_name:
            return None
        return self.plant_map.get(str(common_name).lower().strip())

# Lazy Global Dataset Engine Singleton
_db_engine_instance = None

def get_db_engine():
    global _db_engine_instance
    if _db_engine_instance is None:
        _db_engine_instance = DatasetEngine()
    return _db_engine_instance

# =====================================================
# 3. TEXT NORMALIZATION & BOTANICAL FEATURE EXTRACTOR
# =====================================================

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_botanical_features(text):
    clean = normalize_text(text)
    words = set(clean.split())
    
    extracted = {
        "raw_text": clean,
        "words": words,
        "leaf_shapes": [s for s in LEAF_SHAPE_KEYWORDS if s in clean],
        "leaf_arrangements": [a for a in LEAF_ARRANGEMENT_KEYWORDS if a in clean],
        "leaf_types": [t for t in LEAF_TYPE_KEYWORDS if t in clean],
        "flower_colors": [fc for fc in FLOWER_COLOR_KEYWORDS if fc in clean],
        "flower_types": [f for f in FLOWER_TYPE_KEYWORDS if f in clean],
        "fruit_types": [fr for fr in FRUIT_TYPE_KEYWORDS if fr in clean],
        "stem_roots": [sr for sr in STEM_ROOT_KEYWORDS if sr in clean],
        "plant_types": [pt for pt in PLANT_TYPE_KEYWORDS if pt in clean],
        "habitats": [h for h in HABITAT_KEYWORDS if h in clean],
        "medicinal_uses": [u for u in MEDICINAL_USE_KEYWORDS if u in clean],
        "distinctive_markers": [m for m, weight in DISTINCTIVE_BOTANICAL_MARKERS.items() if m in clean],
        "meaningful_words": {w for w in words if w not in GENERIC_BOTANICAL_STOPWORDS and len(w) > 2}
    }
    return extracted

# =====================================================
# 4. WEIGHTED CATEGORY MATCHER & CANDIDATE RETRIEVER
# =====================================================

def calculate_weighted_match(user_features, plant_row, tfidf_score):
    user_words = user_features["meaningful_words"]
    if not user_words and not user_features["distinctive_markers"] and not user_features["leaf_shapes"] and not user_features["flower_colors"] and not user_features["medicinal_uses"] and not user_features["plant_types"]:
        return 0.0, [], []

    matching_features = []
    mismatching_features = []

    # Category Scores (0.0 to 1.0)
    scores = {
        "leaf": 0.0,
        "flower": 0.0,
        "fruit": 0.0,
        "stem_root": 0.0,
        "plant_type": 0.0,
        "habitat": 0.0,
        "height": 0.0,
        "uses": 0.0,
        "other": 0.0,
        "tfidf": min(1.0, float(tfidf_score))
    }

    # 1. Leaf Attributes (20%)
    p_leaf = (str(plant_row.get("Leaf_Shape_Description", "")) + " " +
              str(plant_row.get("Leaf_Arrangement_Description", "")) + " " +
              str(plant_row.get("Leaf_Type_Description", ""))).lower()
    
    leaf_matches = 0
    for shape in user_features["leaf_shapes"]:
        if shape in p_leaf:
            leaf_matches += 1
            matching_features.append(f"Leaf Shape: {shape}")
        else:
            mismatching_features.append(f"Leaf Shape expected '{shape}' but dataset has '{plant_row.get('Leaf_Shape_Description')}'")

    for arr in user_features["leaf_arrangements"]:
        if arr in p_leaf:
            leaf_matches += 1
            matching_features.append(f"Leaf Arrangement: {arr}")

    for ltype in user_features["leaf_types"]:
        if ltype in p_leaf:
            leaf_matches += 1
            matching_features.append(f"Leaf Type: {ltype}")

    if user_features["leaf_shapes"] or user_features["leaf_arrangements"] or user_features["leaf_types"]:
        scores["leaf"] = min(1.0, leaf_matches / max(1, len(user_features["leaf_shapes"]) + len(user_features["leaf_arrangements"]) + len(user_features["leaf_types"])))

    # 2. Flower Attributes (15%)
    p_flower = (str(plant_row.get("Flower_Color_Description", "")) + " " + str(plant_row.get("Flower_Type_Description", ""))).lower()
    flower_matches = 0
    for ftype in user_features["flower_types"]:
        if ftype in p_flower:
            flower_matches += 1
            matching_features.append(f"Flower Type: {ftype}")
        else:
            mismatching_features.append(f"Flower Type expected '{ftype}' but dataset has '{plant_row.get('Flower_Type_Description')}'")

    for fcol in user_features["flower_colors"]:
        if fcol in p_flower:
            flower_matches += 1
            matching_features.append(f"Flower Color: {fcol}")

    if user_features["flower_types"] or user_features["flower_colors"]:
        scores["flower"] = min(1.0, flower_matches / max(1, len(user_features["flower_types"]) + len(user_features["flower_colors"])))

    # 3. Plant Type (10%) & Habitat (10%)
    p_ptype = str(plant_row.get("Plant_Type", "")).lower()
    p_hab = str(plant_row.get("Habitat_Description", "")).lower()
    
    pt_matches = 0
    for pt in user_features["plant_types"]:
        if pt in p_ptype:
            pt_matches += 1
            matching_features.append(f"Plant Type: {pt}")
    if user_features["plant_types"]:
        scores["plant_type"] = min(1.0, pt_matches / len(user_features["plant_types"]))

    hab_matches = 0
    for h in user_features["habitats"]:
        if h in p_hab:
            hab_matches += 1
            matching_features.append(f"Habitat: {h}")
    if user_features["habitats"]:
        scores["habitat"] = min(1.0, hab_matches / len(user_features["habitats"]))

    # Medicinal & Culinary Uses (5%)
    p_uses = (str(plant_row.get("Medicinal_Uses_Description", "")) + " " + str(plant_row.get("Culinary_Uses_Description", ""))).lower()
    uses_matches = 0
    for u in user_features["medicinal_uses"]:
        if u in p_uses:
            uses_matches += 1
            matching_features.append(f"Medicinal Use: {u}")
    if user_features["medicinal_uses"]:
        scores["uses"] = min(1.0, uses_matches / len(user_features["medicinal_uses"]))

    # 4. Fruit Attributes (10%)
    p_fruit = (str(plant_row.get("Fruit_Type_Description", "")) + " " + str(plant_row.get("Fruit_Color_Description", ""))).lower()
    fruit_matches = 0
    for frtype in user_features["fruit_types"]:
        if frtype in p_fruit:
            fruit_matches += 1
            matching_features.append(f"Fruit Type: {frtype}")
        else:
            mismatching_features.append(f"Fruit Type expected '{frtype}' but dataset has '{plant_row.get('Fruit_Type_Description')}'")

    if user_features["fruit_types"]:
        scores["fruit"] = min(1.0, fruit_matches / len(user_features["fruit_types"]))

    # 5. Stem & Root Attributes (10%)
    p_stem = (str(plant_row.get("Stem_Type_Description", "")) + " " + str(plant_row.get("Root_Type_Description", ""))).lower()
    stem_matches = 0
    for sr in user_features["stem_roots"]:
        if sr in p_stem:
            stem_matches += 1
            matching_features.append(f"Stem/Root Trait: {sr}")

    if user_features["stem_roots"]:
        scores["stem_root"] = min(1.0, stem_matches / len(user_features["stem_roots"]))

    # 6. Distinctive Botanical Markers (Heavy Boosts & Contradiction Penalties)
    distinctive_boost = 0.0
    p_full_doc = plant_row.get('search_doc', '')
    for marker in user_features["distinctive_markers"]:
        weight = DISTINCTIVE_BOTANICAL_MARKERS.get(marker, 0.30)
        if marker in p_full_doc:
            distinctive_boost += weight
            matching_features.append(f"Distinctive Feature: {marker}")
        else:
            distinctive_boost -= (weight * 1.5)
            mismatching_features.append(f"Missing Distinctive Feature: {marker}")

    # General Word Match Ratio
    doc_words = set(p_full_doc.split())
    matched_words = user_words.intersection(doc_words)
    word_match_ratio = len(matched_words) / max(1, len(user_words))
    scores["other"] = word_match_ratio

    # Calculate Weighted Final Score
    final_score = (
        scores["leaf"] * 0.20 +
        scores["flower"] * 0.15 +
        scores["fruit"] * 0.10 +
        scores["stem_root"] * 0.10 +
        scores["plant_type"] * 0.10 +
        scores["habitat"] * 0.10 +
        scores["height"] * 0.05 +
        scores["uses"] * 0.05 +
        scores["other"] * 0.05 +
        scores["tfidf"] * 0.10 +
        distinctive_boost
    )

    final_score = max(0.0, min(1.0, final_score))
    return final_score, matching_features, mismatching_features

def retrieve_top_candidates(user_input, top_k=5):
    engine = get_db_engine()
    if not engine.plants or not user_input:
        return []

    user_features = extract_botanical_features(user_input)

    candidate_results = []
    for plant in engine.plants:
        weighted_score, match_feats, mismatch_feats = calculate_weighted_match(user_features, plant, tfidf_score=0.0)
        
        candidate_results.append({
            "plant_id": plant.get("Plant_ID"),
            "common_name": plant.get("Common_Name"),
            "scientific_name": plant.get("Scientific_Name"),
            "family": plant.get("Family"),
            "plant_type": plant.get("Plant_Type"),
            "leaf_shape": plant.get("Leaf_Shape_Description"),
            "flower_type": plant.get("Flower_Type_Description"),
            "fruit_type": plant.get("Fruit_Type_Description"),
            "habitat": plant.get("Habitat_Description"),
            "score": round(weighted_score, 4),
            "matching_features": match_feats,
            "mismatching_features": mismatch_feats,
            "raw_row": plant
        })

    candidate_results.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = candidate_results[:top_k]

    # DEBUG LOGGING
    print("\n" + "="*70)
    print(f"[DEBUG LOG] USER INPUT: '{user_input}'")
    print(f"[DEBUG LOG] EXTRACTED FEATURES: {user_features}")
    print(f"[DEBUG LOG] TOP {len(top_candidates)} RETRIEVED CANDIDATES FROM DATASET:")
    for idx, c in enumerate(top_candidates):
        print(f"   #{idx+1} Candidate: {c['common_name']} ({c['scientific_name']}) | Weighted Score: {c['score']*100:.1f}%")
        print(f"       Matching Features: {c['matching_features']}")
        print(f"       Mismatching Features: {c['mismatching_features']}")
    print("="*70 + "\n")

    return top_candidates

# =====================================================
# 5. GEMINI BOTANICAL VERIFICATION & REASONING ENGINE
# =====================================================

def verify_with_gemini(user_input, top_candidates):
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()

    if not top_candidates:
        return {
            "predicted_plant": None,
            "scientific_name": None,
            "confidence": 0,
            "matching_features": [],
            "mismatching_features": ["No candidate plants available"],
            "reason": "No candidates found in dataset",
            "status": "UNCERTAIN"
        }

    # Prepare structured candidate list for Gemini
    formatted_candidates = []
    for idx, c in enumerate(top_candidates):
        formatted_candidates.append({
            "candidate_index": idx + 1,
            "Common_Name": c["common_name"],
            "Scientific_Name": c["scientific_name"],
            "Family": c["family"],
            "Plant_Type": c["plant_type"],
            "Leaf_Shape": c["leaf_shape"],
            "Flower_Type": c["flower_type"],
            "Fruit_Type": c["fruit_type"],
            "Habitat": c["habitat"],
            "Retrieved_Match_Score": f"{c['score']*100:.1f}%",
            "Observed_Matches": c["matching_features"],
            "Observed_Mismatches": c["mismatching_features"]
        })

    system_instruction = (
        "You are a strict Botanical Verification Engine. "
        "Your task is to compare the User's Description against ONLY the supplied Candidate Plants retrieved from the dataset. "
        "CRITICAL RULES:\n"
        "1. NEVER invent or introduce a plant name that is NOT present in the supplied candidates.\n"
        "2. Compare the user's description with the supplied dataset attributes for each candidate.\n"
        "3. Generic characteristics ('green leaves', 'tree', 'medicinal', 'tropical') are weak evidence.\n"
        "4. Distinctive botanical characteristics ('drip tip', 'cordate', 'syconium', 'rhizome', 'prop root', 'needle-like') are strong evidence.\n"
        "5. Strongly penalize contradictions. If user description contradicts a candidate's distinct traits, reject that candidate.\n"
        "6. If evidence is weak or uncertain (confidence < 60%), set status to 'UNCERTAIN' and set predicted_plant to null.\n"
        "7. Respond STRICTLY in JSON format with keys: predicted_plant, scientific_name, confidence, matching_features, mismatching_features, reason, status."
    )

    prompt = f"""USER DESCRIPTION: "{user_input}"

SUPPLIED DATASET CANDIDATES:
{json.dumps(formatted_candidates, indent=2)}

Analyze the user description against these dataset candidates and return strictly JSON:
{{
  "predicted_plant": "Exact Common_Name from supplied candidates or null if uncertain",
  "scientific_name": "Exact Scientific_Name from supplied candidates or null if uncertain",
  "confidence": integer_0_to_100,
  "matching_features": ["list of confirmed matching traits"],
  "mismatching_features": ["list of contradictory or missing traits"],
  "reason": "Detailed botanical reasoning for decision",
  "status": "CONFIDENT or UNCERTAIN"
}}"""

    url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}'
    headers = {'Content-Type': 'application/json'}
    payload = {
        'contents': [{'parts': [{'text': f"{system_instruction}\n\n{prompt}"}]}]
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            
            content_text = ""
            if 'candidates' in res_json and len(res_json['candidates']) > 0:
                content_text = res_json['candidates'][0]['content']['parts'][0]['text']

            content_text = re.sub(r'^```json\s*', '', content_text.strip())
            content_text = re.sub(r'\s*```$', '', content_text.strip())

            result_dict = json.loads(content_text)
            print(f"[DEBUG LOG] GEMINI VERIFICATION RESPONSE:\n{json.dumps(result_dict, indent=2)}")
            return result_dict
    except Exception as e:
        print(f"[DEBUG LOG] Gemini API Exception ({e}). Falling back to weighted dataset verification.")
        
        top = top_candidates[0]
        # Valid botanical match requires >= 2 matching features (or 1 distinctive marker) and weighted score >= 0.18
        has_distinctive = len([m for m in top["matching_features"] if "Distinctive Feature" in m or "Leaf Shape" in m or "Flower Type" in m]) >= 1
        if top["score"] >= 0.18 and (len(top["matching_features"]) >= 2 or has_distinctive):
            calibrated_conf = min(98, max(75, int(top["score"] * 100) + 45))
            return {
                "predicted_plant": top["common_name"],
                "scientific_name": top["scientific_name"],
                "confidence": calibrated_conf,
                "matching_features": top["matching_features"],
                "mismatching_features": top["mismatching_features"],
                "reason": f"Matched dataset species based on {len(top['matching_features'])} confirmed botanical features.",
                "status": "CONFIDENT"
            }
        else:
            return {
                "predicted_plant": None,
                "scientific_name": None,
                "confidence": int(top["score"] * 100),
                "matching_features": top["matching_features"],
                "mismatching_features": top["mismatching_features"],
                "reason": "Evidence is weak, generic, or contradictory across dataset candidates.",
                "status": "UNCERTAIN"
            }

# =====================================================
# 6. STRICT BACKEND VALIDATOR & CONFIDENCE ENGINE
# =====================================================

def execute_plant_identification_pipeline(user_input):
    if not user_input or len(normalize_text(user_input)) < 3:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Please provide a valid plant description to begin identification.",
            "results": []
        }

    # Step 1: Retrieve Top 5 Dataset Candidates
    top_candidates = retrieve_top_candidates(user_input, top_k=5)
    if not top_candidates:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Plant identification is uncertain. Please provide more botanical characteristics.",
            "results": []
        }

    # Step 2: Gemini Botanical Verification
    gemini_res = verify_with_gemini(user_input, top_candidates)

    # Step 3: Strict Backend Validation
    pred_c_name = gemini_res.get("predicted_plant")
    pred_s_name = gemini_res.get("scientific_name")
    confidence = int(gemini_res.get("confidence", 0))
    status = gemini_res.get("status", "UNCERTAIN")

    valid_candidate_names = {c["common_name"].lower(): c for c in top_candidates}
    
    # Check 1: Candidate must exist in top retrieved dataset candidates
    matched_candidate = None
    if pred_c_name and str(pred_c_name).lower() in valid_candidate_names:
        matched_candidate = valid_candidate_names[str(pred_c_name).lower()]
    elif top_candidates and top_candidates[0]["score"] >= 0.55:
        # Check top candidate if Gemini agreed or confidence is strong
        matched_candidate = top_candidates[0]
        confidence = max(confidence, int(matched_candidate["score"] * 100))

    # Check 2: Confidence Threshold & UNCERTAIN rule
    if not matched_candidate or confidence < 60 or status == "UNCERTAIN":
        print(f"[DEBUG LOG] FINAL DECISION: UNCERTAIN (Confidence: {confidence}%)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "confidence": confidence,
            "message": "Plant identification is uncertain. Please provide more botanical characteristics.",
            "results": [],
            "candidates_debug": top_candidates
        }

    # Verify plant record in dataset
    db_record = get_db_engine().get_plant_by_name(matched_candidate["common_name"])
    if not db_record:
        print("[DEBUG LOG] FINAL DECISION: REJECTED (Candidate not found in dataset)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Plant identification is uncertain. Please provide more botanical characteristics.",
            "results": []
        }

    # Verified Final Plant Item
    final_item = {
        "Is_Plant": True,
        "Common_Name": db_record.get("Common_Name"),
        "Scientific_Name": db_record.get("Scientific_Name"),
        "Family": db_record.get("Family", "N/A"),
        "Plant_Type": db_record.get("Plant_Type", "N/A"),
        "Habitat": db_record.get("Habitat_Description", "Not Specified"),
        "Medicinal_Uses": db_record.get("Medicinal_Uses_Description", "Not Specified"),
        "Culinary_Uses": db_record.get("Culinary_Uses_Description", "Not Specified"),
        "Leaf_Shape": db_record.get("Leaf_Shape_Description", "Not Specified"),
        "Flower_Color": db_record.get("Flower_Color_Description", "Not Specified"),
        "Smell": db_record.get("Smell_Description", "Not Specified"),
        "Toxicity": db_record.get("Toxicity_Level_Description", "Low"),
        "Match_Percentage": confidence,
        "Matching_Features": gemini_res.get("matching_features", matched_candidate["matching_features"]),
        "Mismatching_Features": gemini_res.get("mismatching_features", matched_candidate["mismatching_features"]),
        "Reason": gemini_res.get("reason", f"Matched based on {len(matched_candidate['matching_features'])} botanical characteristics.")
    }

    print(f"[DEBUG LOG] FINAL DECISION: CONFIDENT -> '{final_item['Common_Name']}' ({final_item['Match_Percentage']}%)")
    return {
        "is_plant": True,
        "status": "CONFIDENT",
        "confidence": confidence,
        "results": [final_item],
        "candidates_debug": top_candidates
    }

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "I found a tree with cordate leaves with drip tip and syconium flowers"
    res = execute_plant_identification_pipeline(query)
    print("\nPIPELINE RESULT JSON:")
    print(json.dumps(res, indent=2))
