import pandas as pd
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# =========================
# LOAD DATASET
# =========================
df = pd.read_csv("3.csv")

# Fill missing values
df = df.fillna("")

# =========================
# CREATE TEXT CORPUS
# =========================
def combine_features(row):
    return " ".join([
        row["Common_Name"],
        row["Scientific_Name"],
        row["Family"],
        row["Plant_Type"],
        row["Leaf_Shape"],
        row["Flower_Color"],
        row["Habitat"],
        row["Medicinal_Uses"],
        row["Culinary_Uses"],
        row["Industrial_Uses"]
    ])

df["combined_text"] = df.apply(combine_features, axis=1)

# =========================
# TF-IDF TRAINING
# =========================
tfidf = TfidfVectorizer(stop_words="english")
tfidf_matrix = tfidf.fit_transform(df["combined_text"])

# =========================
# SEMANTIC EMBEDDING MODEL
# =========================
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
sbert_embeddings = sbert_model.encode(df["combined_text"], show_progress_bar=True)

# =========================
# SAVE TRAINED COMPONENTS
# =========================
with open("tfidf_vectorizer.pkl", "wb") as f:
    pickle.dump(tfidf, f)

with open("tfidf_matrix.pkl", "wb") as f:
    pickle.dump(tfidf_matrix, f)

with open("sbert_embeddings.pkl", "wb") as f:
    pickle.dump(sbert_embeddings, f)

df.to_pickle("plants_dataframe.pkl")

print("✅ Model training complete and saved.")
