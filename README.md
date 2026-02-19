# 🌿 Text-Based Plant Identification using NLP

## 📌 Project Overview
The **Text-Based Plant Identification System** is an NLP-driven application that identifies plant species based on textual descriptions provided by the user. The system analyzes semantic meaning and keyword relevance to return the most relevant plant matches along with similarity scores and detailed botanical information.

This project demonstrates the practical use of **Natural Language Processing (NLP)** and **semantic similarity techniques** in plant identification.

---

## 🎯 Objectives
- Identify plants using natural language descriptions.
- Provide **top matching plant results** with similarity percentage.
- Display botanical and usage details.
- Implement semantic search using NLP.
- Develop an interactive web interface for real-time prediction.

---

## 🧠 Technologies Used

### Programming & Framework
- Python 3
- Flask

### NLP & Machine Learning
- TF-IDF Vectorization
- Sentence Transformers (SBERT)
- Cosin Similarity
- Hybrid Similarity Scorin

### Libraries
- pandas  
- scikit-learn  
- sentence-transformers  
- numpy  
- flask  

---

## ⚙️ System Architecture

### 🔹 Data Processing
Plant attributes are combined into a single textual representation for semantic analysis.

### 🔹 Feature Extraction
- TF-IDF → keyword importance  
- SBERT embeddings → semantic understanding  

### 🔹 Hybrid Matching Formula

```
Final Score =
(0.4 × TF-IDF similarity)
+ (0.6 × Semantic similarity)
```

### 🔹 Output
- Top matching plants
- Match percentage
- Complete plant details

---

## 📂 Project Structure

```
PlantProject/
│
├── app.py                 # Flask web app
├── predict.py             # Prediction engine
├── formatter.py           # Output formatting
├── train_model.py         # Model training
├── 3.csv                  # Plant dataset
│
├── plants_dataframe.pkl   # processed data
├── sbert_embeddings.pkl   # semantic vectors
├── tfidf_matrix.pkl       # TF-IDF vectors
├── tfidf_vectorizer.pkl   # TF-IDF model
│
└── templates/
    └── index.html         # Web interface
```

---

## 🚀 How to Run the Project

### 1️⃣ Install Dependencies

```bash
pip install pandas scikit-learn sentence-transformers flask numpy
```

---

### 2️⃣ Train the Model (Run Once)

```bash
python train_model.py
```

---

### 3️⃣ Run the Web Application

```bash
python app.py
```

---

### 4️⃣ Open in Browser

```
http://127.0.0.1:5000
```

---

## 🧪 Example Input

```
medicinal plant used for skin diseases
```

## ✅ Example Output

- Neem — 92%
- Tulsi — 85%
- Aloe Vera — 80%

(with detailed plant information)

---

## 🌟 Key Features

✔ NLP-based plant identification  
✔ Semantic similarity matching  
✔ Hybrid scoring for high accuracy  
✔ Top-N predictions with confidence score  
✔ Interactive web interface  
✔ Scalable dataset design  

---

## 📊 Applications

- Botanical research assistance  
- Educational tools  
- Herbal & medicinal plant identification  
- Agricultural knowledge systems  
- Biodiversity documentation  

---

## 🔮 Future Enhancements

- Image-based plant identification  
- Mobile application development  
- Voice-based plant queries  
- Regional language support  
- Cloud deployment  

---

## 👨‍🎓 Academic Significance

This project demonstrates:

- Natural Language Processing
- Semantic Search Systems
- Information Retrieval Techniques
- Machine Learning Integration
- AI-based Web Application Development

---

## 📜 License
This project is developed for academic and educational purposes.

---

## 🙌 Acknowledgment
Developed as a Final Year Engineering Project to explore NLP-based semantic plant identification.
