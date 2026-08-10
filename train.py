import pandas as pd
import numpy as np
import re
import joblib
from sentence_transformers import SentenceTransformer

# =====================================================
# LOAD DATASET
# =====================================================

print("Loading dataset...")

try:
    df = pd.read_csv("plants.csv")
except Exception:
    df = pd.read_csv("plants.csv", encoding="latin1")

print(f"Dataset loaded successfully [OK] ({len(df)} rows)")

# Fill empty values
df = df.fillna("")

# =====================================================
# CLEAN TEXT FUNCTION
# =====================================================

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# =====================================================
# ALL BOTANICAL FEATURE COLUMNS
# =====================================================

all_columns = [
    "Common_Name",
    "Scientific_Name",
    "Family",
    "Kingdom",
    "Class",
    "Order",
    "Plant_Type",
    "Life_Span",
    "Leaf_Type_Description",
    "Leaf_Arrangement_Description",
    "Leaf_Shape_Description",
    "Stem_Type_Description",
    "Stem_Texture_Description",
    "Flower_Color_Description",
    "Flower_Type_Description",
    "Flowering_Season",
    "Fruit_Type_Description",
    "Fruit_Color_Description",
    "Root_Type_Description",
    "Habitat_Description",
    "Native_Region_India",
    "Medicinal_Uses_Description",
    "Culinary_Uses_Description",
    "Industrial Use Description",
    "Toxicity_Level_Description",
    "Text Input",
    "Smell_Description"
]

existing_columns = [col for col in all_columns if col in df.columns]
print(f"Indexed columns ({len(existing_columns)}): {existing_columns}")

# =====================================================
# COMBINE ALL TEXT FOR NLP EMBEDDINGS
# =====================================================

combined_texts = []

for _, row in df.iterrows():
    parts = []
    for col in existing_columns:
        val = str(row[col]).strip()
        if val:
            parts.append(val)
    
    raw_combined = " ".join(parts)
    cleaned = clean_text(raw_combined)
    combined_texts.append(cleaned)

df["combined_text"] = combined_texts

print("Text preparation completed [OK]")

# =====================================================
# LOAD AI MODEL & GENERATE EMBEDDINGS
# =====================================================

print("Loading SentenceTransformer model ('all-MiniLM-L6-v2')...")
model = SentenceTransformer('all-MiniLM-L6-v2')

print("Generating sentence embeddings for all plants...")
embeddings = model.encode(combined_texts, show_progress_bar=True)

print("Embeddings generated successfully [OK] Shape:", embeddings.shape)

# =====================================================
# SAVE AI ARTIFACTS
# =====================================================

print("Saving AI dataset and embeddings...")

joblib.dump(embeddings, "embeddings.pkl")
joblib.dump(df, "data.pkl")

print("======================================")
print("HIGH ACCURACY AI MODEL REBUILT & READY [OK]")
print("======================================")