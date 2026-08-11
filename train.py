import pandas as pd
import numpy as np
import re
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

print("==========================================================")
print("STARTING BOTANICAL ML MODEL RETRAINING & INDEXING")
print("==========================================================")

try:
    df = pd.read_csv("plants.csv")
except Exception:
    df = pd.read_csv("plants.csv", encoding="latin1")

df = df.fillna("")
print(f"[OK] Loaded dataset: {len(df)} plant records")

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

all_columns = [
    "Common_Name", "Scientific_Name", "Family", "Kingdom", "Class", "Order",
    "Plant_Type", "Life_Span", "Leaf_Type_Description", "Leaf_Arrangement_Description",
    "Leaf_Shape_Description", "Stem_Type_Description", "Stem_Texture_Description",
    "Flower_Color_Description", "Flower_Type_Description", "Flowering_Season",
    "Fruit_Type_Description", "Fruit_Color_Description", "Root_Type_Description",
    "Habitat_Description", "Native_Region_India", "Medicinal_Uses_Description",
    "Culinary_Uses_Description", "Industrial Use Description", "Toxicity_Level_Description",
    "Text Input", "Smell_Description"
]

existing_columns = [col for col in all_columns if col in df.columns]

combined_texts = []
vocab_words = set()

for _, row in df.iterrows():
    parts = []
    for col in existing_columns:
        val = str(row[col]).strip()
        if val:
            parts.append(val)
            cleaned_val = clean_text(val)
            for w in cleaned_val.split():
                if len(w) > 2 and not w.isdigit():
                    vocab_words.add(w)
    
    raw_combined = " ".join(parts)
    cleaned = clean_text(raw_combined)
    combined_texts.append(cleaned)

df["combined_text"] = combined_texts

# Add known botanical terms to vocabulary
botanical_terms = {
    "leaf", "leaves", "flower", "flowers", "tree", "trees", "plant", "plants",
    "shrub", "herb", "herbs", "root", "roots", "stem", "stems", "fruit", "fruits",
    "seed", "seeds", "bark", "branch", "bloom", "foliage", "petal", "petals",
    "aroma", "scent", "medicinal", "culinary", "succulent", "palm", "vine",
    "rhizome", "drupe", "berry", "capsule", "taproot", "fibrous", "lanceolate",
    "ovate", "elliptic", "pinnate", "panicle", "spike", "raceme", "drupe", "syconium"
}
vocab_words.update(botanical_terms)

# =====================================================
# BUILD & TRAIN TF-IDF VECTORIZER + NEAREST NEIGHBORS
# =====================================================

print("\n1. Training TfidfVectorizer (unigrams + bigrams)...")
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    sublinear_tf=True,
    min_df=1,
    stop_words='english'
)

tfidf_matrix = vectorizer.fit_transform(combined_texts)
print(f"[OK] TF-IDF Matrix shape: {tfidf_matrix.shape}")

print("2. Fitting Cosine Similarity NearestNeighbors Classifier...")
nn_model = NearestNeighbors(n_neighbors=5, metric='cosine', algorithm='brute')
nn_model.fit(tfidf_matrix)
print("[OK] NearestNeighbors Model fit complete")

# =====================================================
# SAVE ALL ARTIFACTS
# =====================================================

print("\n3. Saving model artifacts...")
joblib.dump(vectorizer, "vectorizer.pkl")
joblib.dump(nn_model, "model.pkl")
joblib.dump(tfidf_matrix, "vectors.pkl")
joblib.dump(df, "data.pkl")
joblib.dump(vocab_words, "vocab.pkl")

print("==========================================================")
print("RETRAINING COMPLETED SUCCESSFULLY [100% OK]")
print(f"Indexed {len(df)} plant records and {len(vocab_words)} botanical terms.")
print("Model files updated: vectorizer.pkl, model.pkl, vectors.pkl, data.pkl, vocab.pkl")
print("==========================================================")