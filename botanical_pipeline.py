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
    "pome", "schizocarp"
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
    "shrub/small tree"
}

# HABITAT: from Habitat_Description column
HABITAT_KEYWORDS = {
    "tropical", "subtropical", "dry forests", "rainforests", "wetlands",
    "marshes", "ponds", "lakes", "coastal", "arid", "semi-arid",
    "villages", "gardens", "moist forests", "river banks", "wasteland",
    "dry deciduous", "humid", "mangrove"
}

# STEM TEXTURE: from Stem_Texture_Description
STEM_TEXTURE_KEYWORDS = {
    "rough", "smooth", "hairy", "serrated", "thorny", "spiny", "glabrous"
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
        self.load_dataset()

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
        "leaf_shapes":       [k for k in LEAF_SHAPE_KEYWORDS if k in clean],
        "leaf_arrangements": [k for k in LEAF_ARRANGEMENT_KEYWORDS if k in clean],
        "leaf_types":        [k for k in LEAF_TYPE_KEYWORDS if k in clean],
        "flower_colors":     [k for k in FLOWER_COLOR_KEYWORDS if k in clean],
        "flower_types":      [k for k in FLOWER_TYPE_KEYWORDS if k in clean],
        "fruit_types":       [k for k in FRUIT_TYPE_KEYWORDS if k in clean],
        "stem_roots":        [k for k in STEM_ROOT_KEYWORDS if k in clean],
        "plant_types":       [k for k in PLANT_TYPE_KEYWORDS if k in clean],
        "habitats":          [k for k in HABITAT_KEYWORDS if k in clean],
        "stem_textures":     [k for k in STEM_TEXTURE_KEYWORDS if k in clean],
        "seasons":           [k for k in SEASON_KEYWORDS if k in clean],
        "distinctive_markers": [k for k in DISTINCTIVE_BOTANICAL_MARKERS if k in clean],
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
        len(features["stem_roots"]) +
        len(features["plant_types"]) +
        len(features["habitats"]) +
        len(features["distinctive_markers"])
    )

    return features


# =====================================================
# SECTION 4: STRUCTURED FEATURE MATCHING
# =====================================================

def calculate_structured_match(user_features, plant_row):
    """
    Calculates a structured botanical match score between user description
    and a single dataset plant row.

    Returns: (score: float, matching_features: list, mismatching_features: list)

    RULES:
    - Species name exact match = 0.99 (bypass all other scoring)
    - Generic words contribute ZERO score
    - Score is based on ACTUAL evidence, not word ratio
    - Contradiction (user says X, plant has Y) applies penalty
    - Minimum threshold: score >= 0.40 AND >=2 matching features for CONFIDENT
    """
    raw_user = user_features["raw_text"]
    c_name = str(plant_row.get("Common_Name", "")).lower().strip()
    s_name = str(plant_row.get("Scientific_Name", "")).lower().strip()

    matching_features = []
    mismatching_features = []

    # --- SPECIES NAME EXACT MATCH (highest priority) ---
    # User typed the exact plant name or it appears prominently in text.
    # NAME MATCH ALWAYS RETURNS 1.0 to win over any botanical feature match.
    if c_name and len(c_name) > 3:
        words_in_input = set(raw_user.split())
        c_name_words = c_name.split()

        if c_name == raw_user:
            # Entire input is just the plant name
            return 1.0, [f"Exact Name Match: {plant_row.get('Common_Name')}"], []

        if len(c_name_words) >= 2 and c_name in raw_user:
            # Multi-word name (e.g. "Holy Basil") appears anywhere in input
            return 1.0, [f"Exact Name Match: {plant_row.get('Common_Name')}"], []

        if len(c_name_words) == 1:
            # Single-word name: match if word appears in input (any length)
            # But exclude generic color/descriptor words that aren't distinctive plant identifiers
            GENERIC_NAME_BLOCKLIST = {
                "yellow", "blue", "red", "white", "green", "black", "pink", "orange",
                "purple", "violet", "gold", "silver", "giant", "wild", "common",
                "small", "large", "tall", "dwarf", "bitter", "sweet", "false",
                "indian", "chinese", "japanese", "african", "american", "rare"
            }
            if c_name in words_in_input and c_name not in GENERIC_NAME_BLOCKLIST:
                return 1.0, [f"Exact Name Match: {plant_row.get('Common_Name')}"], []
        else:
            # Multi-word name: primary word must be >= 5 chars to avoid color/descriptor false matches
            # Also exclude generic descriptors used as primary words of multi-word names
            GENERIC_PRIMARY_BLOCKLIST = {
                "yellow", "blue", "red", "white", "green", "black", "pink", "orange",
                "purple", "violet", "gold", "silver", "giant", "wild", "common",
                "small", "large", "tall", "dwarf", "bitter", "sweet", "false",
                "indian", "chinese", "japanese", "african", "american", "rare"
            }
            c_name_primary = c_name_words[0]
            if (len(c_name_primary) >= 5 and c_name_primary in words_in_input
                    and c_name_primary not in GENERIC_PRIMARY_BLOCKLIST):
                return 1.0, [f"Exact Name Match: {plant_row.get('Common_Name')}"], []

    if s_name and len(s_name) > 8:
        # Full scientific name in input
        if s_name in raw_user:
            return 1.0, [f"Scientific Name Match: {plant_row.get('Scientific_Name')}"], []

    # --- STRUCTURED CATEGORY SCORING ---
    # Each category is scored 0.0-1.0 independently.
    # A category only gets score if user MENTIONED that category.
    # Missing data from user = skip that category (no penalty).

    category_scores = {}
    weights = {
        "leaf":       0.22,
        "flower":     0.18,
        "fruit":      0.12,
        "stem_root":  0.12,
        "plant_type": 0.10,
        "habitat":    0.08,
        "season":     0.05,
        "stem_tex":   0.05,
        "distinctive": 0.08,   # handled separately with boosts
    }

    # 1. LEAF ATTRIBUTES (22%)
    plant_leaf = (
        str(plant_row.get("Leaf_Shape_Description", "")).lower() + " " +
        str(plant_row.get("Leaf_Arrangement_Description", "")).lower() + " " +
        str(plant_row.get("Leaf_Type_Description", "")).lower()
    )
    leaf_hits = 0
    leaf_total = (len(user_features["leaf_shapes"]) +
                  len(user_features["leaf_arrangements"]) +
                  len(user_features["leaf_types"]))

    for shape in user_features["leaf_shapes"]:
        if shape in plant_leaf:
            leaf_hits += 1
            matching_features.append(f"Leaf Shape: {shape}")
        else:
            mismatching_features.append(
                f"Leaf Shape '{shape}' not in dataset ({plant_row.get('Leaf_Shape_Description')})"
            )

    for arr in user_features["leaf_arrangements"]:
        if arr in plant_leaf:
            leaf_hits += 1
            matching_features.append(f"Leaf Arrangement: {arr}")
        else:
            mismatching_features.append(
                f"Leaf Arrangement '{arr}' not in dataset ({plant_row.get('Leaf_Arrangement_Description')})"
            )

    for ltype in user_features["leaf_types"]:
        if ltype in plant_leaf:
            leaf_hits += 1
            matching_features.append(f"Leaf Type: {ltype}")

    if leaf_total > 0:
        category_scores["leaf"] = leaf_hits / leaf_total
    # else: category skipped (user didn't mention leaves)

    # 2. FLOWER ATTRIBUTES (18%)
    plant_flower = (
        str(plant_row.get("Flower_Color_Description", "")).lower() + " " +
        str(plant_row.get("Flower_Type_Description", "")).lower()
    )
    flower_hits = 0
    flower_total = (len(user_features["flower_colors"]) +
                    len(user_features["flower_types"]))

    for fcol in user_features["flower_colors"]:
        if fcol in plant_flower:
            flower_hits += 1
            matching_features.append(f"Flower Color: {fcol}")
        else:
            mismatching_features.append(
                f"Flower Color '{fcol}' not in dataset ({plant_row.get('Flower_Color_Description')})"
            )

    for ftype in user_features["flower_types"]:
        if ftype in plant_flower:
            flower_hits += 1
            matching_features.append(f"Flower Type: {ftype}")
        else:
            mismatching_features.append(
                f"Flower Type '{ftype}' not in dataset ({plant_row.get('Flower_Type_Description')})"
            )

    if flower_total > 0:
        category_scores["flower"] = flower_hits / flower_total

    # 3. FRUIT ATTRIBUTES (12%)
    plant_fruit = (
        str(plant_row.get("Fruit_Type_Description", "")).lower() + " " +
        str(plant_row.get("Fruit_Color_Description", "")).lower()
    )
    fruit_hits = 0
    fruit_total = len(user_features["fruit_types"])

    for frtype in user_features["fruit_types"]:
        if frtype in plant_fruit:
            fruit_hits += 1
            matching_features.append(f"Fruit Type: {frtype}")
        else:
            mismatching_features.append(
                f"Fruit Type '{frtype}' not in dataset ({plant_row.get('Fruit_Type_Description')})"
            )

    if fruit_total > 0:
        category_scores["fruit"] = fruit_hits / fruit_total

    # 4. STEM & ROOT ATTRIBUTES (12%)
    plant_stem = (
        str(plant_row.get("Stem_Type_Description", "")).lower() + " " +
        str(plant_row.get("Root_Type_Description", "")).lower()
    )
    stem_hits = 0
    stem_total = len(user_features["stem_roots"])

    for sr in user_features["stem_roots"]:
        if sr in plant_stem:
            stem_hits += 1
            matching_features.append(f"Stem/Root: {sr}")
        else:
            mismatching_features.append(
                f"Stem/Root '{sr}' not in dataset"
            )

    if stem_total > 0:
        category_scores["stem_root"] = stem_hits / stem_total

    # 5. PLANT TYPE (10%)
    plant_type = str(plant_row.get("Plant_Type", "")).lower()
    pt_hits = 0
    pt_total = len(user_features["plant_types"])

    for pt in user_features["plant_types"]:
        if pt in plant_type:
            pt_hits += 1
            matching_features.append(f"Plant Type: {pt}")
        else:
            mismatching_features.append(
                f"Plant Type '{pt}' not in dataset ({plant_row.get('Plant_Type')})"
            )

    if pt_total > 0:
        category_scores["plant_type"] = pt_hits / pt_total

    # 6. HABITAT (8%)
    plant_hab = str(plant_row.get("Habitat_Description", "")).lower()
    hab_hits = 0
    hab_total = len(user_features["habitats"])

    for h in user_features["habitats"]:
        if h in plant_hab:
            hab_hits += 1
            matching_features.append(f"Habitat: {h}")

    if hab_total > 0:
        category_scores["habitat"] = hab_hits / hab_total

    # 7. FLOWERING SEASON (5%)
    plant_season = str(plant_row.get("Flowering_Season", "")).lower()
    season_hits = 0
    season_total = len(user_features["seasons"])

    for s in user_features["seasons"]:
        if s in plant_season:
            season_hits += 1
            matching_features.append(f"Flowering Season: {s}")

    if season_total > 0:
        category_scores["season"] = season_hits / season_total

    # 8. STEM TEXTURE (5%)
    plant_tex = str(plant_row.get("Stem_Texture_Description", "")).lower()
    tex_hits = 0
    tex_total = len(user_features["stem_textures"])

    for t in user_features["stem_textures"]:
        if t in plant_tex:
            tex_hits += 1
            matching_features.append(f"Stem Texture: {t}")

    if tex_total > 0:
        category_scores["stem_tex"] = tex_hits / tex_total

    # 9. DISTINCTIVE MARKERS (8%) — heavy boost for specific identifiers
    full_doc = plant_row.get('search_doc', '')
    distinctive_score = 0.0

    for marker in user_features["distinctive_markers"]:
        marker_weight = DISTINCTIVE_BOTANICAL_MARKERS.get(marker, 0.30)
        if marker in full_doc:
            distinctive_score += marker_weight
            matching_features.append(f"Distinctive Marker: {marker}")
        else:
            # Heavy penalty for contradiction (user says rhizome, plant has taproot)
            distinctive_score -= (marker_weight * 1.5)
            mismatching_features.append(f"Distinctive Marker '{marker}' NOT found in dataset")

    # --- COMPUTE WEIGHTED FINAL SCORE ---
    # Only use categories that were explicitly mentioned by user.
    weighted_sum = 0.0
    active_weight_sum = 0.0

    for cat, w in weights.items():
        if cat == "distinctive":
            continue  # Handled separately below
        if cat in category_scores:
            weighted_sum += category_scores[cat] * w
            active_weight_sum += w

    # Normalize to active categories only (don't penalize for unmentioned categories)
    if active_weight_sum > 0:
        normalized_score = weighted_sum / active_weight_sum
    else:
        normalized_score = 0.0

    # Add distinctive marker boost (capped)
    normalized_score += min(0.35, max(-0.25, distinctive_score))

    # Final score clipped to [0.0, 1.0]
    final_score = max(0.0, min(1.0, normalized_score))

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

    candidate_results = []
    for plant in engine.plants:
        score, match_feats, mismatch_feats = calculate_structured_match(user_features, plant)

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
            "score":               round(score, 4),
            "is_name_match":       any("Name Match" in f for f in match_feats),
            "matching_features":   match_feats,
            "mismatching_features": mismatch_feats,
            "raw_row":             plant,
        })

    # Sort: primary = score DESC, secondary = is_name_match DESC (name matches win ties)
    candidate_results.sort(key=lambda x: (x["score"], 1 if x["is_name_match"] else 0), reverse=True)
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
    if has_species_match and score >= 0.90:
        # User explicitly named the plant
        confidence = min(99, int(score * 100))
        return {
            "predicted_plant": top["common_name"],
            "scientific_name": top["scientific_name"],
            "confidence": confidence,
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": "User explicitly named the plant; verified in dataset.",
            "status": "CONFIDENT"
        }
    elif has_distinctive and match_count >= 2 and score >= 0.40:
        confidence = min(92, int(score * 100) + 20)
        return {
            "predicted_plant": top["common_name"],
            "scientific_name": top["scientific_name"],
            "confidence": confidence,
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": f"Matched {match_count} distinctive botanical features from dataset.",
            "status": "CONFIDENT"
        }
    elif match_count >= 3 and mismatch_count == 0 and score >= 0.40:
        confidence = min(85, int(score * 100) + 10)
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
            "confidence": int(score * 100),
            "matching_features": top["matching_features"],
            "mismatching_features": top["mismatching_features"],
            "reason": "Evidence is insufficient or contradictory to make a confident prediction.",
            "status": "UNCERTAIN"
        }


# =====================================================
# SECTION 7: STRICT VALIDATION & FINAL PIPELINE
# =====================================================

def execute_plant_identification_pipeline(user_input):
    """
    Main pipeline entry point.

    Returns dict:
    {
        "is_plant": bool,
        "status": "CONFIDENT" | "UNCERTAIN",
        "confidence": int,
        "message": str (if UNCERTAIN),
        "results": [plant_dict] (if CONFIDENT),
        "candidates_debug": [list of top 5 candidates]
    }
    """
    if not user_input or len(normalize_text(user_input)) < 3:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Please provide a valid plant description.",
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

    # STEP 4: Build verified result from EXACT dataset row
    from plant_images import get_verified_plant_image
    image_info = get_verified_plant_image(
        db_record.get("Common_Name", ""),
        db_record.get("Scientific_Name", "")
    )

    final_item = {
        "Plant_ID":            db_record.get("Plant_ID", ""),
        "Is_Plant":            True,
        "Common_Name":         db_record.get("Common_Name"),
        "Scientific_Name":     db_record.get("Scientific_Name"),
        "Family":              db_record.get("Family", "N/A"),
        "Plant_Type":          db_record.get("Plant_Type", "N/A"),
        "Life_Span":           db_record.get("Life_Span", "N/A"),
        "Habitat":             db_record.get("Habitat_Description", "N/A"),
        "Native_Region":       db_record.get("Native_Region_India", "N/A"),
        "Leaf_Shape":          db_record.get("Leaf_Shape_Description", "N/A"),
        "Leaf_Arrangement":    db_record.get("Leaf_Arrangement_Description", "N/A"),
        "Flower_Color":        db_record.get("Flower_Color_Description", "N/A"),
        "Flower_Type":         db_record.get("Flower_Type_Description", "N/A"),
        "Fruit_Type":          db_record.get("Fruit_Type_Description", "N/A"),
        "Stem_Type":           db_record.get("Stem_Type_Description", "N/A"),
        "Root_Type":           db_record.get("Root_Type_Description", "N/A"),
        "Medicinal_Uses":      db_record.get("Medicinal_Uses_Description", "N/A"),
        "Culinary_Uses":       db_record.get("Culinary_Uses_Description", "N/A"),
        "Industrial_Uses":     db_record.get("Industrial Use Description", "N/A"),
        "Toxicity":            db_record.get("Toxicity_Level_Description", "N/A"),
        "Smell":               db_record.get("Smell_Description", "N/A"),
        "Flowering_Season":    db_record.get("Flowering_Season", "N/A"),
        "Match_Percentage":    confidence,
        "Matching_Features":   gemini_res.get("matching_features", matched_candidate["matching_features"]),
        "Mismatching_Features": gemini_res.get("mismatching_features", []),
        "Reason":              gemini_res.get("reason", ""),
        # IMAGE — only verified sources, never random
        "Photo_Url":           image_info["url"],
        "Photo_Source":        image_info["source"],
        "Is_Verified_Image":   image_info["is_verified"],
    }

    print(f"[DEBUG] FINAL DECISION: CONFIDENT -> '{final_item['Common_Name']}' "
          f"({final_item['Match_Percentage']}%) | Plant_ID={final_item['Plant_ID']} | "
          f"Image verified={image_info['is_verified']}")

    return {
        "is_plant":        True,
        "status":          "CONFIDENT",
        "confidence":      confidence,
        "results":         [final_item],
        "candidates_debug": top_candidates
    }


if __name__ == "__main__":
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "Neem tree with lanceolate leaves and white panicle flowers"
    result = execute_plant_identification_pipeline(query)
    print("\nFINAL PIPELINE RESULT:")
    print(json.dumps(result, indent=2, default=str))
