
import pickle
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

# =========================
# LOAD TRAINED FILES
# =========================
tfidf = pickle.load(open("tfidf_vectorizer.pkl", "rb"))
tfidf_matrix = pickle.load(open("tfidf_matrix.pkl", "rb"))
sbert_embeddings = pickle.load(open("sbert_embeddings.pkl", "rb"))
df = pd.read_pickle("plants_dataframe.pkl")

# load SBERT model
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

# =========================
# PREDICTION FUNCTION
# =========================
def predict_plant(user_input, top_n=5):

    # TF-IDF similarity
    user_tfidf = tfidf.transform([user_input])
    tfidf_scores = cosine_similarity(user_tfidf, tfidf_matrix)[0]

    # Semantic similarity
    user_embedding = sbert_model.encode([user_input])
    semantic_scores = cosine_similarity(user_embedding, sbert_embeddings)[0]

    # Hybrid scoring
    final_scores = (0.4 * tfidf_scores) + (0.6 * semantic_scores)

    # Get best matches
    best_idx = np.argsort(final_scores)[::-1][:top_n]

    results = []

    for i in best_idx:
        plant_data = df.iloc[i].to_dict()
        plant_data["Match_Percentage"] = round(final_scores[i] * 100, 2)
        results.append(plant_data)

    return results


# =========================
# TEST RUN (Terminal)
# =========================
from formatter import format_results, print_results

if __name__ == "__main__":
    query = input("Enter plant description: ")
    matches = predict_plant(query)

    formatted = format_results(matches)
    print_results(formatted)

