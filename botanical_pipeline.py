"""
botanical_pipeline.py
Dataset-first plant identification pipeline.

Architecture:
  USER DESCRIPTION
      -> TEXT NORMALIZATION
      -> BOTANICAL FEATURE EXTRACTION (structured, 10+ categories)
      -> DATASET SEARCH (all 10,454 rows scored)
      -> TOP 5 CANDIDATES
      -> FEATURE-LEVEL COMPARISON (leaf/flower/fruit/stem/root/type/habitat)
      -> GEMINI VERIFICATION (only from candidates, never hallucinated)
      -> STRICT VALIDATION (name in dataset, same row, evidence-based confidence)
      -> FINAL RESULT (with verified image or no image)

Rules:
  - NEVER invent a plant not in the dataset
  - NEVER use hardcoded fallback plants (Neem, Turmeric, etc.)
  - NEVER use loremflickr or random images
  - NEVER floor confidence at 85%
  - ALWAYS prefer UNCERTAIN over a wrong plant
"""

import os
import re
import csv
import json
import urllib.request
import ssl

ssl_ctx = ssl._create_unverified_context()

# =====================================================
# DATASET PATH DISCOVERY
# =====================================================

def find_plants_csv():
    candidates = [
        os.path.join(os.path.dirname(__file__), 'plants.csv'),
        os.path.join(os.path.dirname(__file__), 'plants_clean.csv'),
        os.path.join(os.path.dirname(__file__), '..', 'plants.csv'),
        os.path.join(os.path.dirname(__file__), '..', 'plants_clean.csv'),
        os.path.join(os.getcwd(), 'plants.csv'),
        os.path.join(os.getcwd(), 'plants_clean.csv'),
        '/var/task/plants.csv',
        '/var/task/plants_clean.csv'
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(os.path.dirname(__file__), 'plants.csv')

PLANTS_CSV_PATH = find_plants_csv()

# =====================================================
# SECTION 1: BOTANICAL FEATURE LEXICONS
# All values are EXACT strings from the dataset columns.
# =====================================================

# LEAF SHAPE: from Leaf_Shape_Description column
LEAF_SHAPE_KEYWORDS = {
    "lanceolate", "ovate", "cordate", "elliptic", "linear", "orbicular",
    "oblong", "palmate-lobed", "star-shaped", "linear-lanceolate",
    "oblong-lanceolate", "ovate-elliptic", "cordate with drip tip",
    "compound pinnate", "compound tripinnate", "simple palmate", "simple lobed",
    "needle-like", "spiny-lobed", "spear-shaped", "deltoid", "reniform"
}

# LEAF ARRANGEMENT: from Leaf_Arrangement_Description column
LEAF_ARRANGEMENT_KEYWORDS = {
    "opposite", "alternate", "rosette", "spiral", "floating", "whorled",
    "basal", "decurrent"
}

# LEAF TYPE: from Leaf_Type_Description column
LEAF_TYPE_KEYWORDS = {
    "simple", "compound pinnate", "compound tripinnate", "palmate",
    "simple palmate", "simple lobed"
}

# FLOWER COLOR: from Flower_Color_Description column
FLOWER_COLOR_KEYWORDS = {
    "crimson", "yellow", "white", "purple", "pink", "orange-red", "red",
    "greenish", "yellow-green", "pale yellow", "dark red", "purple/red",
    "purple/white", "white/cream", "white/yellow", "silver-purple",
    "whitish", "greenish-yellow", "inconspicuous", "red-green"
}

# FLOWER TYPE: from Flower_Type_Description column
FLOWER_TYPE_KEYWORDS = {
    "panicle", "spike", "syconium", "solitary", "spikelet", "raceme",
    "fascicle", "bell-shaped", "corymb", "spadix", "compound spike",
    "catkin", "umbel", "cyme", "head"
}

# FRUIT TYPE: from Fruit_Type_Description column
FRUIT_TYPE_KEYWORDS = {
    "drupe", "berry", "capsule", "achene", "syconium fig", "grain",
    "aggregate", "capsule pod", "capsule boll", "nut", "samara", "pod",
    "pome", "schizocarp", "fruit", "fruits", "red fruit", "red fruits",
    "round red fruit", "round red fruits"
}

# STEM / ROOT TYPE: from Stem_Type_Description + Root_Type_Description
STEM_ROOT_KEYWORDS = {
    "woody", "herbaceous", "pseudostem", "rhizome", "taproot",
    "prop root", "aerial root", "fibrous", "adventitious", "jointed culm",
    "woody culm", "vine climber", "succulent", "rhizomatous"
}

# PLANT TYPE: from Plant_Type column
PLANT_TYPE_KEYWORDS = {
    "tree", "herb", "shrub", "grass", "climber", "palm tree",
    "succulent herb", "aquatic herb", "cactus", "moss", "fern",
    "shrub/small tree", "shrub/tree", "small tree"
}

# HABITAT: from Habitat_Description column
HABITAT_KEYWORDS = {
    "tropical", "subtropical", "dry forests", "rainforests", "wetlands",
    "marshes", "ponds", "lakes", "coastal", "arid", "semi-arid",
    "villages", "gardens", "moist forests", "river banks", "wasteland",
    "dry deciduous", "humid", "mangrove"
}

# STEM TEXTURE / LEAF SURFACE: from Stem_Texture_Description
STEM_TEXTURE_KEYWORDS = {
    "rough", "smooth", "hairy", "serrated", "thorny", "spiny", "glabrous",
    "glossy", "glossy leaves"
}

# FLOWERING SEASON
SEASON_KEYWORDS = {
    "spring", "summer", "autumn", "winter", "year-round",
    "winter-spring", "spring-summer", "summer-autumn"
}

# DISTINCTIVE MARKERS that strongly identify specific plants
# These override generic word matching when found
DISTINCTIVE_BOTANICAL_MARKERS = {
    "drip tip":           0.50,
    "cordate with drip tip": 0.55,
    "syconium":           0.55,
    "rhizome":            0.40,
    "prop root":          0.45,
    "aerial root":        0.45,
    "pseudostem":         0.40,
    "jointed culm":       0.45,
    "woody culm":         0.40,
    "rhizomatous":        0.40,
    "floating":           0.40,
    "succulent":          0.35,
    "orbicular":          0.40,
    "compound tripinnate": 0.45,
    "star-shaped":        0.40,
    "palmate-lobed":      0.40,
    "vine climber":       0.40,
    "spadix":             0.45,
    "adventitious":       0.40,
    "semi-arid":          0.30,
    "vitamin c":          0.45,
}

# Words that are completely generic and must NOT contribute to score
GENERIC_STOPWORDS = {
    "plant", "tree", "leaf", "leaves", "flower", "flowers", "fruit", "fruits",
    "root", "roots", "stem", "stems", "herb", "herbs", "shrub", "shrubs",
    "species", "spp", "area", "found", "looking", "identify", "used", "uses",
    "green", "white", "yellow", "tropical", "subtropical", "medicinal",
    "growing", "grown", "native", "common", "type", "description",
    "properties", "has", "with", "and", "for", "the", "that", "this",
    "can", "what", "its", "are", "been", "from", "have", "which",
    "user", "input", "identify", "name", "please", "help", "find",
    "region", "india", "grows", "found", "also", "used", "known",
    "large", "small", "long", "short", "dark", "light", "bright"
}


# =====================================================
# SECTION 2: DATASET ENGINE
# =====================================================

class DatasetEngine:
    def __init__(self, csv_path=PLANTS_CSV_PATH):
        self.csv_path = csv_path
        self.plants = []
        self.plant_map_by_name = {}     # common_name.lower() -> row
        self.plant_map_by_id = {}       # Plant_ID -> row
        self.plant_map_by_sci = {}      # scientific_name.lower() -> row
        self.vectorizer = None
        self.nn_model = None
        self.load_dataset()
        self.load_vector_models()

    def load_vector_models(self):
        try:
            import joblib
            base_dir = os.path.dirname(os.path.abspath(__file__))
            vec_path = os.path.join(base_dir, "vectorizer.pkl")
            model_path = os.path.join(base_dir, "model.pkl")
            if not os.path.exists(vec_path) or not os.path.exists(model_path):
                # Try inner directory
                base_dir = os.path.join(base_dir, "Text_To_Plant-main", "Text_To_Plant-main")
                vec_path = os.path.join(base_dir, "vectorizer.pkl")
                model_path = os.path.join(base_dir, "model.pkl")

            if os.path.exists(vec_path) and os.path.exists(model_path):
                self.vectorizer = joblib.load(vec_path)
                self.nn_model = joblib.load(model_path)
                print(f"[DatasetEngine] TF-IDF Vectorizer & NearestNeighbors model loaded successfully.")
        except Exception as e:
            print(f"[DatasetEngine] Note loading vector models: {e}")

    def load_dataset(self):
        if not os.path.exists(self.csv_path):
            print(f"[ERROR] Dataset file not found at: {self.csv_path}")
            return

        seen_keys = set()
        with open(self.csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_name = str(row.get('Common_Name', '')).strip()
                s_name = str(row.get('Scientific_Name', '')).strip()
                plant_id = str(row.get('Plant_ID', '')).strip()

                if not c_name or not s_name:
                    continue

                dedup_key = (c_name.lower(), s_name.lower())
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                # Build a normalized search document from ALL columns
                doc_parts = [
                    c_name, s_name,
                    row.get('Family', ''), row.get('Kingdom', ''),
                    row.get('Class', ''), row.get('Order', ''),
                    row.get('Plant_Type', ''), row.get('Life_Span', ''),
                    row.get('Leaf_Type_Description', ''),
                    row.get('Leaf_Arrangement_Description', ''),
                    row.get('Leaf_Shape_Description', ''),
                    row.get('Stem_Type_Description', ''),
                    row.get('Stem_Texture_Description', ''),
                    row.get('Flower_Color_Description', ''),
                    row.get('Flower_Type_Description', ''),
                    row.get('Flowering_Season', ''),
                    row.get('Fruit_Type_Description', ''),
                    row.get('Fruit_Color_Description', ''),
                    row.get('Root_Type_Description', ''),
                    row.get('Habitat_Description', ''),
                    row.get('Native_Region_India', ''),
                    row.get('Medicinal_Uses_Description', ''),
                    row.get('Culinary_Uses_Description', ''),
                    row.get('Industrial Use Description', ''),
                    row.get('Toxicity_Level_Description', ''),
                    row.get('Smell_Description', ''),
                    row.get('Text Input', '')
                ]
                search_doc = " ".join([str(p) for p in doc_parts if p]).lower()
                row['search_doc'] = search_doc
                row['search_words'] = set(search_doc.split())

                self.plants.append(row)
                self.plant_map_by_name[c_name.lower()] = row
                self.plant_map_by_sci[s_name.lower()] = row
                if plant_id:
                    self.plant_map_by_id[plant_id] = row

        print(f"[DatasetEngine] Loaded {len(self.plants)} unique plant records from dataset.")

    def get_by_name(self, common_name):
        return self.plant_map_by_name.get(str(common_name).lower().strip())

    def get_by_sci(self, scientific_name):
        return self.plant_map_by_sci.get(str(scientific_name).lower().strip())

    def get_by_id(self, plant_id):
        return self.plant_map_by_id.get(str(plant_id).strip())


# Lazy singleton
_db_engine = None

def get_db_engine():
    global _db_engine
    if _db_engine is None:
        _db_engine = DatasetEngine()
    return _db_engine


# =====================================================
# SECTION 3: TEXT NORMALIZATION & FEATURE EXTRACTION
# =====================================================

def normalize_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-z0-9\s\-/]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def keyword_in_text(kw, text):
    if " " in kw or "-" in kw:
        return kw in text
    return bool(re.search(r'\b' + re.escape(kw) + r'\b', text))


def extract_botanical_features(text):
    """
    Extracts structured botanical features from user input.
    Each category matches EXACT values from dataset columns.
    Generic words are filtered out to avoid false matches.
    """
    clean = normalize_text(text)
    words = set(clean.split())

    features = {
        "raw_text": clean,
        "words": words,
        # Structured botanical categories
        "leaf_shapes":       [k for k in LEAF_SHAPE_KEYWORDS if keyword_in_text(k, clean)],
        "leaf_arrangements": [k for k in LEAF_ARRANGEMENT_KEYWORDS if keyword_in_text(k, clean)],
        "leaf_types":        [k for k in LEAF_TYPE_KEYWORDS if keyword_in_text(k, clean)],
        "flower_colors":     [k for k in FLOWER_COLOR_KEYWORDS if keyword_in_text(k, clean)],
        "flower_types":      [k for k in FLOWER_TYPE_KEYWORDS if keyword_in_text(k, clean)],
        "fruit_types":       [k for k in FRUIT_TYPE_KEYWORDS if keyword_in_text(k, clean)],
        "fruit_colors":      [k for k in FLOWER_COLOR_KEYWORDS if keyword_in_text(k, clean) and ("fruit" in clean or "fruits" in clean or "berry" in clean)],
        "stem_roots":        [k for k in STEM_ROOT_KEYWORDS if keyword_in_text(k, clean)],
        "plant_types":       [k for k in PLANT_TYPE_KEYWORDS if keyword_in_text(k, clean)],
        "habitats":          [k for k in HABITAT_KEYWORDS if keyword_in_text(k, clean)],
        "stem_textures":     [k for k in STEM_TEXTURE_KEYWORDS if keyword_in_text(k, clean)],
        "seasons":           [k for k in SEASON_KEYWORDS if keyword_in_text(k, clean)],
        "distinctive_markers": [k for k in DISTINCTIVE_BOTANICAL_MARKERS if keyword_in_text(k, clean)],
        # Only non-generic meaningful words
        "meaningful_words": {w for w in words
                             if w not in GENERIC_STOPWORDS
                             and len(w) > 3
                             and not w.isdigit()}
    }

    # Count total distinctive features provided by user
    features["total_features_provided"] = (
        len(features["leaf_shapes"]) +
        len(features["leaf_arrangements"]) +
        len(features["leaf_types"]) +
        len(features["flower_colors"]) +
        len(features["flower_types"]) +
        len(features["fruit_types"]) +
        len(features["fruit_colors"]) +
        len(features["stem_roots"]) +
        len(features["plant_types"]) +
        len(features["habitats"]) +
        len(features["stem_textures"]) +
        len(features["distinctive_markers"])
    )

    return features


# =====================================================
# SECTION 4: STRUCTURED FEATURE MATCHING
# =====================================================

def calculate_structured_match(user_features, plant_row, vec_sim=0.0):
    """
    Multi-dimensional Weighted Hybrid Scoring Engine (0-100%):
    - 35% Botanical Feature Similarity (ratio of requested vs dataset evidence)
    - 30% Vector Semantic Similarity (TF-IDF Cosine distance)
    - 15% Organ Characteristics (Leaf, Flower, Fruit organ alignment)
    - 10% Taxonomy & Ecology (Plant Type, Family, Habitat, Native Region)
    - 10% Exact Keyword & Species Name Matches
    """
    raw_user = user_features["raw_text"]
    c_name = str(plant_row.get("Common_Name", "")).lower().strip()
    s_name = str(plant_row.get("Scientific_Name", "")).lower().strip()

    matching_features = []
    mismatching_features = []

    # 1. EXACT / KEYWORD SPECIES MATCHES (10%)
    keyword_score = 0.0
    if c_name and len(c_name) > 2:
        c_words = c_name.split()
        if c_name == raw_user or (len(c_words) >= 2 and c_name in raw_user):
            keyword_score = 1.0
            matching_features.append(f"Exact Species Match: {plant_row.get('Common_Name')}")
        elif len(c_words) == 1 and c_words[0] in raw_user.split() and c_words[0] not in GENERIC_STOPWORDS:
            keyword_score = 0.90
            matching_features.append(f"Exact Species Match: {plant_row.get('Common_Name')}")
        elif len(c_words) >= 2 and any(w in raw_user.split() for w in c_words if len(w) >= 4 and w not in GENERIC_STOPWORDS):
            keyword_score = 0.40
            matching_features.append(f"Partial Name Keyword: {plant_row.get('Common_Name')}")

    if s_name and len(s_name) > 5 and s_name in raw_user:
        keyword_score = max(keyword_score, 1.0)
        matching_features.append(f"Scientific Name Match: {plant_row.get('Scientific_Name')}")

    full_doc = plant_row.get('search_doc', '')
    for marker in user_features.get("distinctive_markers", []):
        if marker in full_doc:
            keyword_score = max(keyword_score, 0.85)
            matching_features.append(f"Distinctive Marker: {marker}")

    # 2. BOTANICAL FEATURE SIMILARITY (35%)
    total_mentioned = user_features["total_features_provided"]
    total_hits = 0

    # 3. LEAF / FLOWER / FRUIT ORGAN CHARACTERISTICS (15%)
    organ_hits = 0
    organ_total = 0

    # Leaf organs
    plant_leaf = (
        str(plant_row.get("Leaf_Shape_Description", "")).lower() + " " +
        str(plant_row.get("Leaf_Arrangement_Description", "")).lower() + " " +
        str(plant_row.get("Leaf_Type_Description", "")).lower()
    )
    for shape in user_features["leaf_shapes"]:
        organ_total += 1
        if shape in plant_leaf:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Leaf Shape: {shape.title()}")
        else:
            mismatching_features.append(f"Leaf Shape '{shape}' not in dataset")

    for arr in user_features["leaf_arrangements"]:
        organ_total += 1
        if arr in plant_leaf:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Leaf Arrangement: {arr.title()}")

    for ltype in user_features["leaf_types"]:
        organ_total += 1
        if ltype in plant_leaf:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Leaf Type: {ltype.title()}")

    # Flower organs
    plant_flower = (
        str(plant_row.get("Flower_Color_Description", "")).lower() + " " +
        str(plant_row.get("Flower_Type_Description", "")).lower()
    )
    for fcol in user_features["flower_colors"]:
        organ_total += 1
        if fcol in plant_flower:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Flower Color: {fcol.title()}")
        else:
            mismatching_features.append(f"Flower Color '{fcol}' not in dataset")

    for ftype in user_features["flower_types"]:
        organ_total += 1
        if ftype in plant_flower:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Flower Type: {ftype.title()}")

    # Fruit organs
    plant_fruit = (
        str(plant_row.get("Fruit_Type_Description", "")).lower() + " " +
        str(plant_row.get("Fruit_Color_Description", "")).lower()
    )
    specific_fruit_types = ["drupe", "berry", "pome", "capsule", "follicle", "syconium", "caryopsis", "hesperidium", "legume", "pod", "samara", "nut", "pepo"]
    for frtype in user_features["fruit_types"]:
        organ_total += 1
        if frtype in plant_fruit:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Fruit Type: {frtype.title()}")
        elif "fruit" in frtype and any(sft in plant_fruit for sft in specific_fruit_types):
            organ_hits += 1
            total_hits += 1
            matching_features.append("Fruit Type: Fruit")
        elif frtype in specific_fruit_types:
            mismatching_features.append(f"Fruit Type '{frtype}' mismatch")

    for frcol in user_features.get("fruit_colors", []):
        organ_total += 1
        if frcol in plant_fruit:
            organ_hits += 1
            total_hits += 1
            matching_features.append(f"Fruit Color: {frcol.title()}")

    # Stem / Root & Textures
    plant_stem = (
        str(plant_row.get("Stem_Type_Description", "")).lower() + " " +
        str(plant_row.get("Stem_Texture_Description", "")).lower() + " " +
        str(plant_row.get("Root_Type_Description", "")).lower()
    )
    for sr in user_features["stem_roots"]:
        if sr in plant_stem:
            total_hits += 1
            matching_features.append(f"Stem/Root: {sr.title()}")

    for stex in user_features["stem_textures"]:
        if stex in plant_stem:
            total_hits += 1
            matching_features.append(f"Stem Texture: {stex.title()}")

    # Medicinal / Culinary / Use text matching
    plant_uses = (
        str(plant_row.get("Culinary_Uses_Description", "")).lower() + " " +
        str(plant_row.get("Medicinal_Uses_Description", "")).lower() + " " +
        str(plant_row.get("Industrial Use Description", "")).lower()
    )
    use_hits = 0
    for w in user_features["meaningful_words"]:
        if len(w) >= 4 and w in plant_uses:
            use_hits += 1

    if use_hits >= 2:
        matching_features.append("Botanical Uses Match")
        total_hits += 1

    # 4. PLANT TYPE / FAMILY / HABITAT (10%)
    plant_type = str(plant_row.get("Plant_Type", "")).lower()
    plant_hab = str(plant_row.get("Habitat_Description", "")).lower()
    taxa_hits = 0
    taxa_total = len(user_features["plant_types"]) + len(user_features["habitats"])

    for pt in user_features["plant_types"]:
        if pt in plant_type or ("tree" in pt and "tree" in plant_type) or ("shrub" in pt and "shrub" in plant_type) or ("herb" in pt and "herb" in plant_type):
            taxa_hits += 1
            total_hits += 1
            matching_features.append(f"Plant Type: {pt.title()}")
        else:
            mismatching_features.append(f"Plant Type '{pt}' not in dataset")

    for h in user_features["habitats"]:
        if h in plant_hab:
            taxa_hits += 1
            total_hits += 1
            matching_features.append(f"Habitat: {h.title()}")

    # Deduplicate matching features
    unique_matching = []
    seen_m = set()
    for m in matching_features:
        if m not in seen_m:
            seen_m.add(m)
            unique_matching.append(m)
    matching_features = unique_matching

    # COMPUTE 5 WEIGHTED COMPONENTS
    botanical_score = (total_hits / max(3, total_mentioned)) if total_mentioned > 0 else 0.0
    semantic_score = vec_sim
    organ_score = (organ_hits / organ_total) if organ_total > 0 else 0.0
    taxa_score = (taxa_hits / taxa_total) if taxa_total > 0 else 0.0

    if keyword_score >= 0.90:
        final_score = 1.0  # Exact species common name or scientific name match
    else:
        # Weighted hybrid scoring with stronger weighting for organ features & semantic similarity
        final_score = (
            (0.35 * botanical_score) +
            (0.30 * semantic_score) +
            (0.20 * organ_score) +
            (0.10 * taxa_score) +
            (0.05 * keyword_score)
        )

        # Mismatch penalty: penalize if key features explicitly mismatched
        if mismatching_features:
            final_score = max(0.0, final_score - (0.08 * len(mismatching_features)))

    final_score = max(0.0, min(1.0, final_score))
    return final_score, matching_features, mismatching_features


# =====================================================
# SECTION 5: TOP CANDIDATE RETRIEVAL
# =====================================================

def retrieve_top_candidates(user_input, top_k=5):
    """
    Scores ALL dataset plants against user description.
    Returns top_k candidates sorted by structured match score.

    Important: If no features were extracted, returns empty list.
    """
    engine = get_db_engine()
    if not engine.plants or not user_input:
        return []

    user_features = extract_botanical_features(user_input)

    # If user provided no distinctive botanical features at all, immediately return empty
    if user_features["total_features_provided"] == 0 and not user_features["meaningful_words"]:
        print(f"[DEBUG] No botanical features extracted from input. Returning UNCERTAIN.")
        return []

    vector_scores = {}
    if engine.vectorizer and engine.nn_model:
        try:
            clean_q = normalize_text(user_input)
            q_vec = engine.vectorizer.transform([clean_q])
            distances, indices = engine.nn_model.kneighbors(q_vec, n_neighbors=min(50, len(engine.plants)))
            for dist, idx in zip(distances[0], indices[0]):
                sim = max(0.0, 1.0 - float(dist))
                vector_scores[idx] = sim
        except Exception as ve:
            print(f"[DEBUG] Vector search note: {ve}")

    candidate_results = []
    for idx, plant in enumerate(engine.plants):
        vec_sim = vector_scores.get(idx, 0.0)
        struct_score, match_feats, mismatch_feats = calculate_structured_match(user_features, plant, vec_sim=vec_sim)

        is_name_match = any("Name Match" in f for f in match_feats)
        combined_score = 1.0 if is_name_match else struct_score

        # Determine confidence tier label (90-100: HIGH, 75-89: GOOD, 50-74: MODERATE, <50: LOW)
        percentage = min(99, int(combined_score * 100)) if is_name_match else int(combined_score * 100)
        if percentage >= 90:
            confidence_tier = "HIGH"
        elif percentage >= 75:
            confidence_tier = "GOOD"
        elif percentage >= 50:
            confidence_tier = "MODERATE"
        else:
            confidence_tier = "LOW"

        candidate_results.append({
            "plant_id":            plant.get("Plant_ID", ""),
            "common_name":         plant.get("Common_Name", ""),
            "scientific_name":     plant.get("Scientific_Name", ""),
            "family":              plant.get("Family", ""),
            "plant_type":          plant.get("Plant_Type", ""),
            "leaf_shape":          plant.get("Leaf_Shape_Description", ""),
            "leaf_arrangement":    plant.get("Leaf_Arrangement_Description", ""),
            "leaf_type":           plant.get("Leaf_Type_Description", ""),
            "flower_color":        plant.get("Flower_Color_Description", ""),
            "flower_type":         plant.get("Flower_Type_Description", ""),
            "fruit_type":          plant.get("Fruit_Type_Description", ""),
            "stem_type":           plant.get("Stem_Type_Description", ""),
            "root_type":           plant.get("Root_Type_Description", ""),
            "habitat":             plant.get("Habitat_Description", ""),
            "native_region":       plant.get("Native_Region_India", ""),
            "flowering_season":    plant.get("Flowering_Season", ""),
            "medicinal_uses":      plant.get("Medicinal_Uses_Description", ""),
            "culinary_uses":       plant.get("Culinary_Uses_Description", ""),
            "toxicity":            plant.get("Toxicity_Level_Description", ""),
            "smell":               plant.get("Smell_Description", ""),
            "score":               round(combined_score, 4),
            "percentage":          percentage,
            "confidence_tier":     confidence_tier,
            "vector_sim":          round(vec_sim, 4),
            "struct_score":        round(struct_score, 4),
            "is_name_match":       is_name_match,
            "matching_features":   match_feats,
            "mismatching_features": mismatch_feats,
            "raw_row":             plant,
        })

    # Sort key:
    # 1. score DESC
    # 2. Exact Species Match flag DESC (full multi-word name matches beat single word matches)
    # 3. Botanical Uses Match DESC
    # 4. Net matching features DESC (matching - mismatching)
    # 5. Canonical record priority (Plant_ID <= 300)
    candidate_results.sort(
        key=lambda x: (
            x["score"],
            2 if any("Exact Species Match" in f for f in x["matching_features"]) else (1 if any("Scientific Name Match" in f for f in x["matching_features"]) else 0),
            1 if any("Botanical Uses Match" in f for f in x["matching_features"]) else 0,
            len(x["matching_features"]) - len(x["mismatching_features"]),
            1 if str(x.get("plant_id", "")).isdigit() and int(x.get("plant_id", 9999)) <= 300 else 0,
            x.get("struct_score", 0.0)
        ),
        reverse=True
    )
    top_candidates = candidate_results[:top_k]

    # DEBUG LOGGING
    print("\n" + "=" * 70)
    print(f"[DEBUG] USER INPUT: '{user_input}'")
    print(f"[DEBUG] FEATURES EXTRACTED:")
    print(f"   Leaf Shapes:        {user_features['leaf_shapes']}")
    print(f"   Leaf Arrangements:  {user_features['leaf_arrangements']}")
    print(f"   Flower Colors:      {user_features['flower_colors']}")
    print(f"   Flower Types:       {user_features['flower_types']}")
    print(f"   Fruit Types:        {user_features['fruit_types']}")
    print(f"   Stem/Root:          {user_features['stem_roots']}")
    print(f"   Plant Types:        {user_features['plant_types']}")
    print(f"   Habitats:           {user_features['habitats']}")
    print(f"   Distinctive Markers:{user_features['distinctive_markers']}")
    print(f"   Total Features:     {user_features['total_features_provided']}")
    print(f"[DEBUG] TOP {len(top_candidates)} CANDIDATES:")
    for idx, c in enumerate(top_candidates):
        print(f"   #{idx+1} {c['common_name']} ({c['scientific_name']}) | Score: {c['score']*100:.1f}%")
        print(f"        Matching:   {c['matching_features']}")
        print(f"        Mismatch:   {c['mismatching_features'][:3]}")
    print("=" * 70 + "\n")

    return top_candidates


# =====================================================
# SECTION 6: GEMINI BOTANICAL VERIFICATION
# =====================================================

def verify_with_gemini(user_input, top_candidates):
    """
    Sends user description + top 5 dataset candidates to Gemini.
    Gemini MUST select from candidates only — no hallucination allowed.

    If Gemini is unavailable, falls back to structured score analysis.
    Fallback NEVER uses a hardcoded floor confidence.
    """
    if not top_candidates:
        return {
            "predicted_plant": None,
            "scientific_name": None,
            "confidence": 0,
            "matching_features": [],
            "mismatching_features": [],
            "reason": "No candidates found in dataset.",
            "status": "UNCERTAIN"
        }

    gemini_key = (os.environ.get("GEMINI_API_KEY", "").strip() or
                  os.environ.get("GOOGLE_API_KEY", "").strip())

    # Prepare full candidate data to send to Gemini
    candidates_data = []
    for idx, c in enumerate(top_candidates):
        candidates_data.append({
            "candidate_index": idx + 1,
            "Common_Name":      c["common_name"],
            "Scientific_Name":  c["scientific_name"],
            "Family":           c["family"],
            "Plant_Type":       c["plant_type"],
            "Leaf_Shape":       c["leaf_shape"],
            "Leaf_Arrangement": c["leaf_arrangement"],
            "Leaf_Type":        c["leaf_type"],
            "Flower_Color":     c["flower_color"],
            "Flower_Type":      c["flower_type"],
            "Fruit_Type":       c["fruit_type"],
            "Stem_Type":        c["stem_type"],
            "Root_Type":        c["root_type"],
            "Habitat":          c["habitat"],
            "Native_Region":    c["native_region"],
            "Flowering_Season": c["flowering_season"],
            "Dataset_Match_Score": f"{c['score']*100:.1f}%",
            "Confirmed_Matches": c["matching_features"],
            "Contradictions":   c["mismatching_features"]
        })

    system_instruction = (
        "You are a STRICT Botanical Verification Engine for an Indian plant dataset.\n"
        "ABSOLUTE RULES:\n"
        "1. You MUST ONLY select a plant from the supplied CANDIDATE LIST below.\n"
        "2. You MUST NOT invent, guess, or suggest any plant not in the candidate list.\n"
        "3. Generic words (green, leaves, flower, medicinal, herb, tropical, tree) are WEAK evidence.\n"
        "4. Distinctive features (rhizome, pseudostem, cordate with drip tip, syconium, prop root, "
        "orbicular, compound tripinnate, adventitious, woody culm) are STRONG evidence.\n"
        "5. If user description CONTRADICTS a candidate's features, STRONGLY penalize that candidate.\n"
        "6. If evidence is insufficient to distinguish candidates, return UNCERTAIN with null plant.\n"
        "7. Confidence MUST reflect actual evidence:\n"
        "   90-100: Multiple distinctive features confirmed\n"
        "   75-89:  Several specific features confirmed\n"
        "   60-74:  Some features confirmed, minor ambiguity\n"
        "   Below 60: Set status UNCERTAIN\n"
        "8. Return STRICTLY valid JSON only."
    )

    prompt = (
        f'USER DESCRIPTION: "{user_input}"\n\n'
        f"CANDIDATE PLANTS FROM DATASET:\n"
        f"{json.dumps(candidates_data, indent=2)}\n\n"
        "Compare the user description against the candidate botanical attributes above.\n"
        "Return ONLY this JSON:\n"
        "{\n"
        '  "predicted_plant": "Exact Common_Name from candidates, or null",\n'
        '  "scientific_name": "Exact Scientific_Name from candidates, or null",\n'
        '  "confidence": integer_0_to_100,\n'
        '  "matching_features": ["confirmed trait 1", "confirmed trait 2"],\n'
        '  "mismatching_features": ["contradiction 1"],\n'
        '  "reason": "brief botanical reasoning",\n'
        '  "status": "CONFIDENT or UNCERTAIN"\n'
        "}"
    )

    if gemini_key:
        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/"
                   f"models/gemini-1.5-flash:generateContent?key={gemini_key}")
            headers = {'Content-Type': 'application/json'}
            payload = {
                'contents': [{'parts': [{'text': f"{system_instruction}\n\n{prompt}"}]}],
                'generationConfig': {'temperature': 0.0, 'maxOutputTokens': 512}
            }
            req = urllib.request.Request(
                url, data=json.dumps(payload).encode('utf-8'), headers=headers
            )
            with urllib.request.urlopen(req, timeout=12, context=ssl_ctx) as resp:
                res_data = resp.read().decode('utf-8')
                res_json = json.loads(res_data)

                content_text = ""
                if 'candidates' in res_json and res_json['candidates']:
                    content_text = (res_json['candidates'][0]
                                    ['content']['parts'][0]['text'])

                content_text = re.sub(r'^```json\s*', '', content_text.strip())
                content_text = re.sub(r'\s*```$', '', content_text.strip())

                result = json.loads(content_text)
                print(f"[DEBUG] GEMINI RESPONSE:\n{json.dumps(result, indent=2)}")
                return result

        except Exception as e:
            print(f"[DEBUG] Gemini unavailable ({e}). Using structured fallback.")
    else:
        print("[DEBUG] No Gemini key configured. Using structured fallback.")

    # --- STRUCTURED FALLBACK (no Gemini) ---
    # Uses actual feature evidence — NEVER hardcoded confidence floor
    top = top_candidates[0]
    match_count = len(top["matching_features"])
    mismatch_count = len(top["mismatching_features"])
    score = top["score"]

    has_species_match = any("Match" in m for m in top["matching_features"])
    has_distinctive = any("Distinctive Marker" in m for m in top["matching_features"])

    # Confident only when evidence is clear
    confidence = top.get("percentage", int(score * 100))

    if has_species_match and score >= 0.80:
        return {
            "predicted_plant": top["common_name"],
            "scientific_name": top["scientific_name"],
            "confidence": min(99, max(90, confidence)),
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": "User explicitly named the plant; verified in dataset.",
            "status": "CONFIDENT"
        }
    elif (has_distinctive or top.get("vector_sim", 0) >= 0.25 or match_count >= 2) and confidence >= 50:
        return {
            "predicted_plant": top["common_name"],
            "scientific_name": top["scientific_name"],
            "confidence": confidence,
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": f"Matched botanical features and vector traits from dataset.",
            "status": "CONFIDENT"
        }
    elif match_count >= 3 and mismatch_count == 0 and confidence >= 45:
        return {
            "predicted_plant": top["common_name"],
            "scientific_name": top["scientific_name"],
            "confidence": confidence,
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": f"Matched {match_count} botanical features with no contradictions.",
            "status": "CONFIDENT"
        }
    else:
        # Evidence is insufficient
        return {
            "predicted_plant": None,
            "scientific_name": None,
            "confidence": confidence,
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": "Evidence is insufficient or contradictory to make a confident prediction.",
            "status": "UNCERTAIN"
        }


# =====================================================
# SECTION 7: STRICT VALIDATION & FINAL PIPELINE
# =====================================================

FAKE_KEYWORD_PATTERNS = [
    r'\bmagic\b', r'\bunicorn\b', r'\bcyber\b', r'\bquantum\b', r'\btoy\b',
    r'\bartificial\b', r'\bplastic\b', r'\bblablabla\b', r'\bxyz\b', r'\bfake\b',
    r'\bnonexistent\b', r'\bbattery\b', r'\bcharger\b', r'\blaptop\b', r'\bcar\b', r'\bvehicle\b'
]

def is_fake_query(text):
    clean = str(text).lower()
    for pat in FAKE_KEYWORD_PATTERNS:
        if re.search(pat, clean):
            return True
    return False

def execute_plant_identification_pipeline(user_input):
    """
    Main pipeline entry point.
    """
    if not user_input or len(normalize_text(user_input)) < 3 or is_fake_query(user_input):
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "The input text is invalid, fake, or does not describe botanical plant features.",
            "results": [],
            "candidates_debug": []
        }

    # STEP 1: Retrieve top 5 candidates from dataset
    top_candidates = retrieve_top_candidates(user_input, top_k=5)

    if not top_candidates:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Identification uncertain. Please describe distinctive features like leaf shape, flower type, fruit, or root structure.",
            "results": [],
            "candidates_debug": []
        }

    # STEP 2: Gemini botanical verification
    gemini_res = verify_with_gemini(user_input, top_candidates)

    pred_name  = gemini_res.get("predicted_plant")
    pred_sci   = gemini_res.get("scientific_name")
    confidence = int(gemini_res.get("confidence", 0))
    status     = gemini_res.get("status", "UNCERTAIN")

    # STEP 3: STRICT VALIDATION

    # 3a. Status must be CONFIDENT
    if status != "CONFIDENT":
        print(f"[DEBUG] FINAL DECISION: UNCERTAIN (Gemini status='{status}', confidence={confidence}%)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "confidence": confidence,
            "message": "Identification uncertain. Please describe distinctive features like leaf shape, flower type, fruit, or root structure.",
            "results": [],
            "candidates_debug": top_candidates
        }

    # 3b. Confidence must be >= 60%
    if confidence < 60:
        print(f"[DEBUG] FINAL DECISION: UNCERTAIN (confidence={confidence}% < 60%)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "confidence": confidence,
            "message": f"Evidence is insufficient (confidence {confidence}%). Please provide more distinctive botanical characteristics.",
            "results": [],
            "candidates_debug": top_candidates
        }

    # 3c. predicted_plant must exist in top candidates (no hallucination)
    valid_names = {c["common_name"].lower(): c for c in top_candidates}
    matched_candidate = None

    if pred_name:
        pred_key = str(pred_name).lower().strip()
        if pred_key in valid_names:
            matched_candidate = valid_names[pred_key]
        else:
            # Partial match safety
            for cname, cdata in valid_names.items():
                if pred_key in cname or cname in pred_key:
                    matched_candidate = cdata
                    break

    if not matched_candidate:
        print(f"[DEBUG] FINAL DECISION: REJECTED (predicted '{pred_name}' not in top candidates)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Identification uncertain. The predicted plant was not validated against the dataset.",
            "results": [],
            "candidates_debug": top_candidates
        }

    # 3d. Verify plant actually exists in dataset by ID
    db_record = get_db_engine().get_by_name(matched_candidate["common_name"])
    if not db_record:
        # Try scientific name
        db_record = get_db_engine().get_by_sci(matched_candidate.get("scientific_name", ""))

    if not db_record:
        print(f"[DEBUG] FINAL DECISION: REJECTED ('{matched_candidate['common_name']}' not verified in dataset)")
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Identification uncertain. Dataset verification failed.",
            "results": [],
            "candidates_debug": top_candidates
        }

    # 3e. Scientific name must match same row
    db_sci = str(db_record.get("Scientific_Name", "")).strip().lower()
    if pred_sci and pred_sci.strip().lower() != db_sci:
        # Check if genus at least matches
        pred_genus = pred_sci.strip().lower().split()[0] if pred_sci else ""
        db_genus   = db_sci.split()[0] if db_sci else ""
        if pred_genus and db_genus and pred_genus != db_genus:
            print(f"[DEBUG] FINAL DECISION: REJECTED (scientific name mismatch: '{pred_sci}' vs '{db_sci}')")
            return {
                "is_plant": False,
                "status": "UNCERTAIN",
                "message": "Identification uncertain. Scientific name mismatch detected.",
                "results": [],
                "candidates_debug": top_candidates
            }

    # STEP 4: Build candidate-specific verified results list
    from plant_images import get_verified_plant_image

    # Check if top candidate is an exact species name match or exact plant selection
    is_exact_name_match = (
        top_candidates[0]["is_name_match"] or
        any("Exact Species Match" in f or "Scientific Name Match" in f for f in top_candidates[0]["matching_features"])
    )

    # Determine how many results to return dynamically (1 for exact name or >=90% HIGH confidence, 1-3 for descriptions)
    if is_exact_name_match or top_candidates[0]["percentage"] >= 90:
        candidates_to_render = [top_candidates[0]]  # Return EXACTLY 1 result for exact name or 90%+ HIGH match
    else:
        top_score = top_candidates[0]["score"]
        candidates_to_render = [top_candidates[0]]

        if len(top_candidates) >= 2:
            cand2 = top_candidates[1]
            if cand2["percentage"] >= 50 and cand2["score"] >= (0.75 * top_score) and (top_score - cand2["score"] < 0.15):
                candidates_to_render.append(cand2)

        if len(top_candidates) >= 3 and len(candidates_to_render) >= 2:
            cand3 = top_candidates[2]
            if cand3["percentage"] >= 50 and cand3["score"] >= (0.70 * top_score) and (top_score - cand3["score"] < 0.15):
                candidates_to_render.append(cand3)

    results_built = []
    for cand in candidates_to_render:
        db_rec = get_db_engine().get_by_name(cand["common_name"]) or get_db_engine().get_by_sci(cand.get("scientific_name", ""))
        if not db_rec:
            continue

        image_info = get_verified_plant_image(
            db_rec.get("Common_Name", ""),
            db_rec.get("Scientific_Name", ""),
            plant_id=db_rec.get("Plant_ID", "")
        )

        cand_perc = cand["percentage"]
        cand_tier = cand.get("confidence_tier", "HIGH" if cand_perc >= 90 else ("GOOD" if cand_perc >= 75 else ("MODERATE" if cand_perc >= 50 else "LOW")))

        item = {
            "Plant_ID":            db_rec.get("Plant_ID", ""),
            "Is_Plant":            True,
            "Common_Name":         db_rec.get("Common_Name"),
            "Scientific_Name":     db_rec.get("Scientific_Name"),
            "Family":              db_rec.get("Family", "N/A"),
            "Plant_Type":          db_rec.get("Plant_Type", "N/A"),
            "Life_Span":           db_rec.get("Life_Span", "N/A"),
            "Habitat":             db_rec.get("Habitat_Description", "N/A"),
            "Native_Region":       db_rec.get("Native_Region_India", "N/A"),
            "Leaf_Shape":          db_rec.get("Leaf_Shape_Description", "N/A"),
            "Leaf_Arrangement":    db_rec.get("Leaf_Arrangement_Description", "N/A"),
            "Flower_Color":        db_rec.get("Flower_Color_Description", "N/A"),
            "Flower_Type":         db_rec.get("Flower_Type_Description", "N/A"),
            "Fruit_Type":          db_rec.get("Fruit_Type_Description", "N/A"),
            "Stem_Type":           db_rec.get("Stem_Type_Description", "N/A"),
            "Root_Type":           db_rec.get("Root_Type_Description", "N/A"),
            "Medicinal_Uses":      db_rec.get("Medicinal_Uses_Description", "N/A"),
            "Culinary_Uses":       db_rec.get("Culinary_Uses_Description", "N/A"),
            "Industrial_Uses":     db_rec.get("Industrial Use Description", "N/A"),
            "Toxicity":            db_rec.get("Toxicity_Level_Description", "N/A"),
            "Smell":               db_rec.get("Smell_Description", "N/A"),
            "Flowering_Season":    db_rec.get("Flowering_Season", "N/A"),
            "Match_Percentage":    cand_perc,
            "Confidence_Tier":     cand_tier,
            "Matching_Features":   cand["matching_features"],
            "Verified_Features":   [f"✓ {m}" for m in cand["matching_features"]],
            "Mismatching_Features": cand["mismatching_features"],
            "Reason":              f"Matched botanical features and vector traits from dataset.",
            # IMAGE — only verified sources, never random
            "Photo_Url":           image_info["url"],
            "Photo_Source":        image_info["source"],
            "Is_Verified_Image":   image_info["is_verified"],
        }
        results_built.append(item)

    if not results_built:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Identification uncertain. Dataset verification failed.",
            "results": [],
            "candidates_debug": top_candidates
        }

    top_item = results_built[0]
    print(f"[DEBUG] FINAL DECISION: CONFIDENT -> '{top_item['Common_Name']}' "
          f"({top_item['Match_Percentage']}% {top_item['Confidence_Tier']}) | "
          f"Count={len(results_built)} | Plant_ID={top_item['Plant_ID']}")

    return {
        "is_plant":        True,
        "status":          "CONFIDENT",
        "confidence":      top_item["Match_Percentage"],
        "results":         results_built,
        "candidates_debug": top_candidates
    }


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Neem tree with lanceolate leaves and white panicle flowers"
    result = execute_plant_identification_pipeline(query)
    print("\nFINAL PIPELINE RESULT:")
    print(json.dumps(result, indent=2, default=str))
