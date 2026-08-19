"""
botanical_pipeline.py
Scientific Multi-Attribute Botanical Identification & Confidence Scoring Engine.
- Multi-attribute trait matching: Leaf, Flower Color/Type, Fruit Type/Color, Plant Type, Stem, Root, Habitat, Medicinal/Culinary Uses, Text Input.
- Substring disambiguation & Contradiction Penalties (e.g. Drupe vs Aggregate, Panicle vs Solitary).
- Exact name priority (1 result).
- Margin calibration (1-3 results).
- Strict uncertainty guardrail for generic descriptions & rejection for non-plant queries.
"""

import os
import re
import csv
import json
import math
from collections import Counter

# =====================================================
# DATASET DISCOVERY
# =====================================================

def find_dataset_file(filename):
    candidates = [
        os.path.join(os.path.dirname(__file__), filename),
        os.path.join(os.path.dirname(__file__), '..', filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), 'Text_To_Plant-main', filename),
        f'/var/task/{filename}'
    ]
    for p in candidates:
        if os.path.exists(p):
            return os.path.abspath(p)
    return os.path.join(os.path.dirname(__file__), filename)

PLANTS_CSV_PATH = find_dataset_file('plants.csv')
PLANTS_XLSX_PATH = find_dataset_file('Plant_Dataset_with_Full_Descriptions.xlsx')


# =====================================================
# SECTION 1: BOTANICAL FEATURE LEXICONS
# =====================================================

LEAF_SHAPE_KEYWORDS = [
    "cordate with drip tip", "linear-lanceolate", "oblong-lanceolate",
    "ovate-elliptic", "compound tripinnate", "compound pinnate",
    "simple palmate", "simple lobed", "fleshy serrated", "thick fleshy",
    "needle-like", "spiny-lobed", "spear-shaped", "palmate-lobed",
    "star-shaped", "lanceolate", "ovate", "cordate", "elliptic",
    "linear", "orbicular", "oblong", "deltoid", "reniform",
    "glossy", "fleshy", "thick", "serrated", "spiny", "leathery",
    "smooth", "pinnate", "tripinnate", "bipinnate", "palmate"
]

LEAF_ARRANGEMENT_KEYWORDS = [
    "opposite", "alternate", "rosette", "spiral", "floating", "whorled",
    "basal", "decurrent"
]

LEAF_TYPE_KEYWORDS = [
    "compound tripinnate", "compound pinnate", "simple palmate",
    "simple lobed", "tripinnate", "pinnate", "palmate", "compound", "simple"
]

FLOWER_COLOR_KEYWORDS = [
    "greenish-yellow", "yellow-green", "orange-red", "bright red",
    "pale yellow", "golden yellow", "dark red", "purple/red", "purple/white",
    "white/cream", "white/yellow", "silver-purple", "red-green", "crimson",
    "scarlet", "lavender", "violet", "whitish", "greenish", "inconspicuous",
    "yellow", "white", "purple", "pink", "red", "orange", "blue"
]

FLOWER_TYPE_KEYWORDS = [
    "compound spike", "solitary large", "bell-shaped", "syconium",
    "spikelet", "panicle", "fascicle", "corymb", "spadix", "catkin",
    "raceme", "umbel", "spike", "solitary", "cyme", "head"
]

FRUIT_TYPE_KEYWORDS = [
    "syconium fig", "capsule pod", "capsule boll", "aggregate",
    "balausta", "drupe", "berry", "capsule", "achene", "grain",
    "nut", "samara", "pod", "pome", "schizocarp", "edible seeds",
    "juicy edible seeds", "round red fruit", "round red", "round fruit", "round"
]

FRUIT_COLOR_KEYWORDS = [
    "yellow-green", "yellow/orange", "yellow-orange", "green-yellow",
    "red-green", "green/brown", "red/black", "orange", "yellow",
    "red", "green", "brown", "black", "purple", "crimson"
]

STEM_ROOT_KEYWORDS = [
    "woody culm", "jointed culm", "vine climber", "prop roots", "prop root",
    "aerial roots", "aerial root", "pseudostem", "rhizomatous", "rhizome",
    "taproot", "fibrous", "adventitious", "succulent", "herbaceous",
    "woody", "culm", "vine", "rough", "smooth", "hairy", "thorny", "spiny"
]

PLANT_TYPE_KEYWORDS = [
    "succulent herb", "aquatic herb", "palm tree", "shrub/small tree",
    "small tree", "succulent", "climber", "cactus", "tree", "herb",
    "shrub", "grass", "palm", "moss", "fern"
]

HABITAT_KEYWORDS = [
    "tropical dry deciduous forests", "tropical moist forests", "tropical dry forests",
    "tropical rainforests", "tropical coastal regions", "tropical forests",
    "tropical humid regions", "dry deciduous", "subtropical", "rainforests",
    "wetlands", "marshes", "ponds", "lakes", "coastal", "arid", "semi-arid",
    "villages", "gardens", "moist forests", "river banks", "wasteland",
    "tropical", "humid", "mangrove"
]

MEDICINAL_CULINARY_KEYWORDS = [
    "anti-inflammatory", "antibacterial", "antifungal", "antiviral",
    "antioxidant", "vitamin c", "digestive", "skin healing", "burns",
    "adaptogen", "immunity", "cardiac tonic", "antidiarrheal", "antiseptic",
    "asthma", "memory enhancer", "anti-anxiety", "antidiabetic", "fruit fresh",
    "pickles", "juices", "curries", "spice", "herbal tea", "seasoning"
]

DISTINCTIVE_BOTANICAL_MARKERS = {
    "drip tip": 0.35,
    "cordate with drip tip": 0.40,
    "syconium": 0.40,
    "rhizome": 0.30,
    "prop root": 0.35,
    "aerial root": 0.35,
    "pseudostem": 0.30,
    "jointed culm": 0.35,
    "woody culm": 0.30,
    "rhizomatous": 0.30,
    "floating": 0.30,
    "succulent": 0.25,
    "compound tripinnate": 0.35,
    "spadix": 0.35,
    "adventitious": 0.30,
    "edible seeds": 0.35,
    "medicinal gel": 0.35,
    "skin burns": 0.30
}

GENERIC_STOPWORDS = {
    "plant", "tree", "leaf", "leaves", "flower", "flowers", "fruit", "fruits",
    "root", "roots", "stem", "stems", "herb", "herbs", "shrub", "shrubs",
    "species", "spp", "area", "found", "looking", "identify", "used", "uses",
    "green", "white", "yellow", "tropical", "subtropical", "medicinal",
    "growing", "grown", "native", "common", "type", "description",
    "properties", "has", "with", "and", "for", "the", "that", "this",
    "can", "what", "its", "are", "been", "from", "have", "which",
    "user", "input", "identify", "name", "please", "help", "find",
    "region", "india", "grows", "found", "also", "known",
    "large", "small", "long", "short", "dark", "light", "bright",
    "like", "good", "part", "give", "tell", "look", "sample", "inside"
}


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_best_keywords(clean_text_input, keyword_list):
    """
    Extracts matched keywords from text prioritizing longer, more specific multi-word phrases.
    Prevents shorter subsets (e.g. 'yellow') from stealing priority when 'pale yellow' is present.
    """
    matched = []
    # Sort keyword_list by length descending
    sorted_keywords = sorted(keyword_list, key=lambda k: len(k), reverse=True)
    text_copy = f" {clean_text_input} "

    for kw in sorted_keywords:
        pattern = r'(?<![a-z0-9])' + re.escape(kw) + r'(?![a-z0-9])'
        if re.search(pattern, text_copy):
            matched.append(kw)
            # Remove matched keyword from temporary copy so shorter sub-tokens aren't duplicated
            text_copy = re.sub(pattern, ' ', text_copy)

    return matched


# =====================================================
# SECTION 2: DATASET & NAME LOOKUP ENGINE
# =====================================================

class DatasetEngine:
    def __init__(self, csv_path=PLANTS_CSV_PATH):
        self.csv_path = csv_path
        self.plants = []
        self.common_name_map = {}
        self.scientific_name_map = {}
        self.alias_map = {}
        self.idf = {}
        self.load_dataset()

    def load_dataset(self):
        if not os.path.exists(self.csv_path) and os.path.exists(PLANTS_XLSX_PATH):
            try:
                import convert_and_train
                convert_and_train.export_and_train()
            except Exception as e:
                print(f"[DatasetEngine] Auto-extraction note: {e}")

        if not os.path.exists(self.csv_path):
            print(f"[ERROR] Dataset CSV not found at {self.csv_path}")
            return

        seen_keys = set()
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

                # Rich multi-field search document
                doc_parts = [
                    c_name, s_name,
                    row.get('Family', ''),
                    row.get('Plant_Type', ''),
                    row.get('Leaf_Shape_Description', ''),
                    row.get('Leaf_Type_Description', ''),
                    row.get('Leaf_Arrangement_Description', ''),
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
                search_doc = clean_text(" ".join([str(p) for p in doc_parts if p]))
                row['search_doc'] = search_doc
                row['search_words'] = set(search_doc.split())

                self.plants.append(row)

                # Exact Name Indexing
                clean_c = clean_text(c_name)
                clean_s = clean_text(s_name)
                self.common_name_map[clean_c] = row
                self.scientific_name_map[clean_s] = row

                # Common aliases
                aliases = [clean_c, f"{clean_c} tree", f"{clean_c} plant", f"{clean_c} herb", f"{clean_c} shrub"]
                if "(" in c_name and ")" in c_name:
                    inside = c_name[c_name.find("(")+1:c_name.find(")")].strip()
                    outside = c_name[:c_name.find("(")].strip()
                    if inside:
                        aliases.extend([clean_text(inside), f"{clean_text(inside)} tree", f"{clean_text(inside)} plant"])
                    if outside:
                        aliases.extend([clean_text(outside), f"{clean_text(outside)} tree", f"{clean_text(outside)} plant"])

                for a in aliases:
                    if a and a not in self.alias_map:
                        self.alias_map[a] = row

        print(f"[DatasetEngine] Loaded {len(self.plants)} botanical records & {len(self.alias_map)} name aliases.")
        self.build_idf_table()

    def build_idf_table(self):
        N = len(self.plants)
        if N == 0:
            return

        doc_freq = Counter()
        for p in self.plants:
            for w in p['search_words']:
                doc_freq[w] += 1

        self.idf = {w: math.log((N + 1) / (df + 1)) + 1.0 for w, df in doc_freq.items()}

    def compute_asymmetric_coverage(self, query_words, plant_doc_words):
        if not query_words:
            return 0.0

        total_weight = sum(self.idf.get(w, 1.0) for w in query_words)
        if total_weight == 0:
            return 0.0

        matched_weight = sum(self.idf.get(w, 1.0) for w in query_words if w in plant_doc_words)
        return matched_weight / total_weight

    def find_exact_name_match(self, raw_input):
        clean = clean_text(raw_input)
        if not clean:
            return None

        # 1. Direct alias or common/sci name
        if clean in self.alias_map:
            return self.alias_map[clean]
        if clean in self.common_name_map:
            return self.common_name_map[clean]
        if clean in self.scientific_name_map:
            return self.scientific_name_map[clean]

        # 2. Stripped prefix matches (e.g. "identify mango tree", "sample pomegranate")
        stripped = re.sub(r'^(identify|what is|find|show me|sample|tell me about)\s+', '', clean).strip()
        if stripped in self.alias_map:
            return self.alias_map[stripped]

        # 3. Standalone short name check
        words = clean.split()
        if len(words) <= 4:
            for name_key, plant_row in self.common_name_map.items():
                if len(name_key) >= 4 and (name_key == clean or name_key in words or f"{name_key} tree" == clean or f"{name_key} plant" == clean):
                    if name_key not in GENERIC_STOPWORDS:
                        return plant_row

        return None


_db_engine = None

def get_db_engine():
    global _db_engine
    if _db_engine is None:
        _db_engine = DatasetEngine()
    return _db_engine


# =====================================================
# SECTION 3: BOTANICAL FEATURE EXTRACTION
# =====================================================

def extract_botanical_features(text):
    clean = clean_text(text)
    words = set(clean.split())

    features = {
        "raw_text": clean,
        "words": words,
        "leaf_shapes":       extract_best_keywords(clean, LEAF_SHAPE_KEYWORDS),
        "leaf_arrangements": extract_best_keywords(clean, LEAF_ARRANGEMENT_KEYWORDS),
        "leaf_types":        extract_best_keywords(clean, LEAF_TYPE_KEYWORDS),
        "flower_colors":     extract_best_keywords(clean, FLOWER_COLOR_KEYWORDS),
        "flower_types":      extract_best_keywords(clean, FLOWER_TYPE_KEYWORDS),
        "fruit_types":       extract_best_keywords(clean, FRUIT_TYPE_KEYWORDS),
        "fruit_colors":      extract_best_keywords(clean, FRUIT_COLOR_KEYWORDS),
        "stem_roots":        extract_best_keywords(clean, STEM_ROOT_KEYWORDS),
        "plant_types":       extract_best_keywords(clean, PLANT_TYPE_KEYWORDS),
        "habitats":          extract_best_keywords(clean, HABITAT_KEYWORDS),
        "uses":              extract_best_keywords(clean, MEDICINAL_CULINARY_KEYWORDS),
        "distinctive_markers": [k for k in DISTINCTIVE_BOTANICAL_MARKERS if k in clean],
        "meaningful_words":  [w for w in clean.split() if w not in GENERIC_STOPWORDS and len(w) > 2 and not w.isdigit()]
    }

    distinct_organs = 0
    if features["leaf_shapes"] or features["leaf_arrangements"] or features["leaf_types"]:
        distinct_organs += 1
    if features["flower_colors"] or features["flower_types"]:
        distinct_organs += 1
    if features["fruit_types"] or features["fruit_colors"]:
        distinct_organs += 1
    if features["stem_roots"]:
        distinct_organs += 1
    if features["plant_types"]:
        distinct_organs += 1
    if features["habitats"]:
        distinct_organs += 1
    if features["uses"]:
        distinct_organs += 1

    features["distinct_organs_count"] = distinct_organs
    return features


# =====================================================
# SECTION 4: MULTI-ATTRIBUTE CANDIDATE SCORING
# =====================================================

def score_individual_candidate(user_features, plant_row, idf_engine):
    """
    Computes a strictly independent candidate score based on:
    - Leaf morphology (20%)
    - Flower color & inflorescence (20%)
    - Fruit type & color (20%)
    - Plant type, stem & root (15%)
    - Habitat & medicinal/culinary uses (10%)
    - Asymmetric text & 'Text Input' semantic coverage (15%)
    """
    verified_features = []
    contradiction_count = 0

    p_leaf = clean_text(str(plant_row.get("Leaf_Shape_Description", "")) + " " +
                        str(plant_row.get("Leaf_Arrangement_Description", "")) + " " +
                        str(plant_row.get("Leaf_Type_Description", "")))
    p_flower_col = clean_text(str(plant_row.get("Flower_Color_Description", "")))
    p_flower_type = clean_text(str(plant_row.get("Flower_Type_Description", "")))
    p_flower = f"{p_flower_col} {p_flower_type}"

    p_fruit_type = clean_text(str(plant_row.get("Fruit_Type_Description", "")))
    p_fruit_col = clean_text(str(plant_row.get("Fruit_Color_Description", "")))
    p_fruit = f"{p_fruit_type} {p_fruit_col}"

    p_stem = clean_text(str(plant_row.get("Stem_Type_Description", "")) + " " +
                        str(plant_row.get("Root_Type_Description", "")) + " " +
                        str(plant_row.get("Stem_Texture_Description", "")))
    p_type = clean_text(str(plant_row.get("Plant_Type", "")))
    p_hab = clean_text(str(plant_row.get("Habitat_Description", "")))
    p_uses = clean_text(str(plant_row.get("Medicinal_Uses_Description", "")) + " " +
                        str(plant_row.get("Culinary_Uses_Description", "")))
    p_text_input = clean_text(str(plant_row.get("Text Input", "")))
    full_doc = plant_row.get("search_doc", "")

    # 1. LEAF TRAITS (Weight: 20%)
    leaf_pts = 0.0
    leaf_tot = 0.0
    for s in user_features["leaf_shapes"]:
        leaf_tot += 1.0
        if s in p_leaf or s in p_text_input:
            leaf_pts += 1.0
            verified_features.append(f"Leaf Shape: {s.title()}")
        else:
            contradiction_count += 0.5

    for a in user_features["leaf_arrangements"]:
        leaf_tot += 1.0
        if a in p_leaf or a in p_text_input:
            leaf_pts += 1.0
            verified_features.append(f"Leaf Arrangement: {a.title()}")

    for t in user_features["leaf_types"]:
        leaf_tot += 1.0
        if t in p_leaf or t in p_text_input:
            leaf_pts += 1.0
            verified_features.append(f"Leaf Type: {t.title()}")

    score_leaf = (leaf_pts / leaf_tot) if leaf_tot > 0 else 0.50

    # 2. FLOWER TRAITS (Weight: 20%)
    fl_pts = 0.0
    fl_tot = 0.0
    for c in user_features["flower_colors"]:
        fl_tot += 1.0
        if c in p_flower_col or c in p_text_input:
            fl_pts += 1.0
            verified_features.append(f"Flower Color: {c.title()}")
        else:
            contradiction_count += 0.5

    for t in user_features["flower_types"]:
        fl_tot += 1.0
        if t in p_flower_type or t in p_text_input:
            fl_pts += 1.0
            verified_features.append(f"Flower Type: {t.title()}")
        else:
            contradiction_count += 0.5

    score_flower = (fl_pts / fl_tot) if fl_tot > 0 else 0.50

    # 3. FRUIT TRAITS (Weight: 20%)
    fr_pts = 0.0
    fr_tot = 0.0
    for ft in user_features["fruit_types"]:
        fr_tot += 1.0
        if ft in p_fruit_type or ft in p_text_input or (ft in ["round", "round fruit", "round red", "edible seeds"] and ft in full_doc):
            fr_pts += 1.0
            verified_features.append(f"Fruit Type: {ft.title()}")
        else:
            contradiction_count += 1.0  # Strong contradiction on fruit mismatch (e.g. Drupe vs Aggregate)

    for fc in user_features["fruit_colors"]:
        fr_tot += 1.0
        if fc in p_fruit_col or fc in p_text_input:
            fr_pts += 1.0
            verified_features.append(f"Fruit Color: {fc.title()}")
        else:
            contradiction_count += 0.5

    score_fruit = (fr_pts / fr_tot) if fr_tot > 0 else 0.50

    # 4. PLANT TYPE & STEM/ROOT (Weight: 15%)
    pt_pts = 0.0
    pt_tot = 0.0
    for pt in user_features["plant_types"]:
        pt_tot += 1.0
        if pt in p_type or ("small tree" in pt and "tree" in p_type) or (pt in p_text_input):
            pt_pts += 1.0
            verified_features.append(f"Plant Type: {pt.title()}")
        else:
            contradiction_count += 0.5

    for sr in user_features["stem_roots"]:
        pt_tot += 1.0
        if sr in p_stem or sr in p_text_input:
            pt_pts += 1.0
            verified_features.append(f"Stem/Root: {sr.title()}")

    score_plant_type = (pt_pts / pt_tot) if pt_tot > 0 else 0.50

    # 5. HABITAT & USES (Weight: 10%)
    use_pts = 0.0
    use_tot = 0.0
    for h in user_features["habitats"]:
        use_tot += 1.0
        if h in p_hab or h in p_text_input:
            use_pts += 1.0
            verified_features.append(f"Habitat: {h.title()}")

    for u in user_features["uses"]:
        use_tot += 1.0
        if u in p_uses or u in p_text_input:
            use_pts += 1.0
            verified_features.append(f"Use/Property: {u.title()}")

    score_uses = (use_pts / use_tot) if use_tot > 0 else 0.50

    # 6. SEMANTIC / TEXT INPUT COVERAGE (Weight: 15%)
    score_coverage = idf_engine.compute_asymmetric_coverage(user_features["meaningful_words"], plant_row.get("search_words", set()))
    
    # Exact Text Input boost if user query matches the dataset's Text Input description
    if p_text_input and user_features["raw_text"] in p_text_input:
        score_coverage = 1.0
        verified_features.append("Dataset Description Match")

    # Diagnostic markers
    for m in user_features["distinctive_markers"]:
        if m in full_doc:
            verified_features.append(f"Diagnostic Feature: {m.title()}")

    # Determine active weights (only weight categories user actually queried)
    active_weights = {}
    if leaf_tot > 0: active_weights["leaf"] = 0.20
    if fl_tot > 0:   active_weights["flower"] = 0.20
    if fr_tot > 0:   active_weights["fruit"] = 0.20
    if pt_tot > 0:   active_weights["plant_type"] = 0.15
    if use_tot > 0:  active_weights["uses"] = 0.10
    active_weights["coverage"] = 0.15

    total_weight = sum(active_weights.values())
    raw_composite = (
        active_weights.get("leaf", 0.0) * score_leaf +
        active_weights.get("flower", 0.0) * score_flower +
        active_weights.get("fruit", 0.0) * score_fruit +
        active_weights.get("plant_type", 0.0) * score_plant_type +
        active_weights.get("uses", 0.0) * score_uses +
        active_weights.get("coverage", 0.0) * score_coverage
    ) / total_weight

    # Penalize contradictions on specific physical traits (e.g. user queried Drupe, plant has Aggregate follicles)
    if contradiction_count > 0 and fr_tot > 0 and score_fruit == 0:
        raw_composite *= 0.65  # Heavy penalty when fruit type directly contradicts query

    # Calibrate candidate-specific score based on organ count and alignment
    matched_organs = 0
    if any("Leaf" in v for v in verified_features): matched_organs += 1
    if any("Flower" in v for v in verified_features): matched_organs += 1
    if any("Fruit" in v for v in verified_features): matched_organs += 1
    if any("Plant Type" in v or "Stem/Root" in v for v in verified_features): matched_organs += 1
    if any("Use" in v or "Habitat" in v for v in verified_features): matched_organs += 1

    if matched_organs >= 3 and raw_composite >= 0.85 and contradiction_count == 0:
        calibrated_score = min(0.96, raw_composite * 1.05)
    elif matched_organs >= 2 and raw_composite >= 0.75 and contradiction_count <= 1:
        calibrated_score = min(0.90, raw_composite)
    else:
        calibrated_score = raw_composite

    return round(calibrated_score, 4), verified_features


# =====================================================
# SECTION 5: PIPELINE EXECUTION & INTELLIGENT RANKING
# =====================================================

def execute_plant_identification_pipeline(user_input):
    if not user_input or len(clean_text(user_input)) < 3:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Please provide a botanical plant description or upload a photo.",
            "results": [],
            "candidates_debug": []
        }

    engine = get_db_engine()
    if not engine.plants:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "message": "Botanical dataset not loaded.",
            "results": [],
            "candidates_debug": []
        }

    from plant_images import VERIFIED_PLANT_IMAGES

    # 1. EXACT NAME MATCHING PRIORITY (1 Result)
    exact_plant = engine.find_exact_name_match(user_input)
    if exact_plant:
        c_name = exact_plant.get("Common_Name", "")
        s_name = exact_plant.get("Scientific_Name", "")
        c_name_lower = c_name.strip().lower()
        img_info = VERIFIED_PLANT_IMAGES.get(c_name_lower, {})
        photo_url = img_info.get("url") if isinstance(img_info, dict) else None

        verified_feats = [
            f"Common Name: {c_name}",
            f"Scientific Name: {s_name}",
            f"Plant Type: {exact_plant.get('Plant_Type', 'Plant')}",
            f"Family: {exact_plant.get('Family', '')}"
        ]
        if exact_plant.get("Flower_Color_Description"):
            verified_feats.append(f"Flower Color: {exact_plant.get('Flower_Color_Description')}")
        if exact_plant.get("Fruit_Type_Description"):
            verified_feats.append(f"Fruit: {exact_plant.get('Fruit_Type_Description')}")

        result_item = {
            "Common_Name":        c_name,
            "Scientific_Name":    s_name,
            "Family":             exact_plant.get("Family", ""),
            "Plant_Type":         exact_plant.get("Plant_Type", ""),
            "Leaf_Shape":         exact_plant.get("Leaf_Shape_Description") or "Not Specified",
            "Flower_Color":       exact_plant.get("Flower_Color_Description") or "Not Specified",
            "Habitat":            exact_plant.get("Habitat_Description") or "Not Specified",
            "Medicinal_Uses":     exact_plant.get("Medicinal_Uses_Description") or "Not Specified",
            "Culinary_Uses":      exact_plant.get("Culinary_Uses_Description") or "Not Specified",
            "Toxicity":           exact_plant.get("Toxicity_Level_Description") or "None",
            "Smell":              exact_plant.get("Smell_Description") or "Not Specified",
            "Match_Percentage":   95,
            "Confidence_Tier":    "HIGH",
            "Photo_Url":          photo_url,
            "Is_Verified_Image":  bool(photo_url),
            "Matching_Features":  verified_feats,
            "Dataset_Features":   verified_feats,
            "Reason":             f"Exact species verification: {c_name} ({s_name}) confirmed in dataset.",
            "Ai_Explanation":     f"Verified match for {c_name} ({s_name}) in the 10,454-record botanical database."
        }

        return {
            "is_plant": True,
            "status": "CONFIDENT",
            "confidence": 95,
            "confidence_tier": "HIGH",
            "results": [result_item],
            "candidates_debug": [result_item]
        }

    # 2. BOTANICAL TRAIT EXTRACTION
    user_features = extract_botanical_features(user_input)

    # Uncertainty Guardrail: Generic check
    if user_features["distinct_organs_count"] == 0 and len(user_features["meaningful_words"]) < 2:
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "confidence": 30,
            "confidence_tier": "LOW",
            "message": "Plant identification is uncertain. Generic or ambiguous description with no distinctive botanical characteristics.",
            "results": [],
            "candidates_debug": []
        }

    # 3. INDEPENDENT CANDIDATE SCORING
    scored_candidates = []
    for plant in engine.plants:
        score, verified_feats = score_individual_candidate(user_features, plant, engine)
        
        c_name_lower = plant.get('Common_Name', '').strip().lower()
        img_info = VERIFIED_PLANT_IMAGES.get(c_name_lower, {})
        photo_url = img_info.get("url") if isinstance(img_info, dict) else None

        pct = int(score * 100)
        if pct >= 90:
            tier = "HIGH"
        elif pct >= 75:
            tier = "GOOD"
        elif pct >= 60:
            tier = "MODERATE"
        elif pct >= 40:
            tier = "LOW"
        else:
            tier = "VERY LOW"

        scored_candidates.append({
            "plant": plant,
            "score": score,
            "match_percentage": pct,
            "confidence_tier": tier,
            "verified_features": list(dict.fromkeys(verified_feats)),
            "photo_url": photo_url
        })

    # Sort strictly by real score descending
    scored_candidates.sort(key=lambda x: x["score"], reverse=True)

    top_candidate = scored_candidates[0]
    second_candidate = scored_candidates[1] if len(scored_candidates) > 1 else None

    top_score = top_candidate["score"]
    second_score = second_candidate["score"] if second_candidate else 0.0
    margin = top_score - second_score

    # 4. AMBIGUITY & UNCERTAINTY FILTER
    if top_score < 0.45 or (top_score < 0.60 and margin < 0.05 and len(top_candidate["verified_features"]) < 2):
        return {
            "is_plant": False,
            "status": "UNCERTAIN",
            "confidence": top_candidate["match_percentage"],
            "confidence_tier": "LOW",
            "message": "Plant identification is uncertain. Description is too generic or matches multiple plants equally. Please provide more distinctive features.",
            "results": [],
            "candidates_debug": scored_candidates[:3]
        }

    # 5. INTELLIGENT RESULT COUNT SELECTION (1 to 3 Results)
    if top_score >= 0.80 and margin >= 0.15:
        max_results = 1 if (second_score < 0.60 or margin >= 0.25) else 2
    elif top_score >= 0.70:
        max_results = 2 if margin >= 0.10 else 3
    else:
        max_results = 3

    final_results = []
    for c in scored_candidates[:max_results]:
        p = c["plant"]
        final_results.append({
            "Common_Name":        p.get("Common_Name", ""),
            "Scientific_Name":    p.get("Scientific_Name", ""),
            "Family":             p.get("Family", ""),
            "Plant_Type":         p.get("Plant_Type", ""),
            "Leaf_Shape":         p.get("Leaf_Shape_Description") or "Not Specified",
            "Flower_Color":       p.get("Flower_Color_Description") or "Not Specified",
            "Habitat":            p.get("Habitat_Description") or "Not Specified",
            "Medicinal_Uses":     p.get("Medicinal_Uses_Description") or "Not Specified",
            "Culinary_Uses":      p.get("Culinary_Uses_Description") or "Not Specified",
            "Toxicity":           p.get("Toxicity_Level_Description") or "None",
            "Smell":              p.get("Smell_Description") or "Not Specified",
            "Match_Percentage":   c["match_percentage"],
            "Confidence_Tier":    c["confidence_tier"],
            "Photo_Url":          c["photo_url"],
            "Is_Verified_Image":  bool(c["photo_url"]),
            "Matching_Features":  c["verified_features"],
            "Dataset_Features":   c["verified_features"],
            "Reason":             f"Matched {len(c['verified_features'])} botanical characteristics in catalog.",
            "Ai_Explanation":     f"{p.get('Common_Name')} ({p.get('Scientific_Name')}) matches on: {', '.join(c['verified_features'][:4])}."
        })

    return {
        "is_plant": True,
        "status": "CONFIDENT",
        "confidence": final_results[0]["Match_Percentage"],
        "confidence_tier": final_results[0]["Confidence_Tier"],
        "results": final_results,
        "candidates_debug": scored_candidates[:5]
    }
