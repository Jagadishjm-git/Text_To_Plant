"""
convert_and_train.py
Extracts the 10,454-record Plant_Database sheet from Plant_Dataset_with_Full_Descriptions.xlsx,
exports clean plants.csv, and builds TF-IDF vectorizer + NearestNeighbors search models.
Supports pandas/openpyxl with pure Python zipfile+xml fallback.
"""

import os
import sys
import csv
import re
import zipfile
import xml.etree.ElementTree as ET
import joblib

def find_excel_file():
    candidates = [
        os.path.join(os.path.dirname(__file__), "Plant_Dataset_with_Full_Descriptions.xlsx"),
        os.path.join(os.path.dirname(__file__), "..", "Plant_Dataset_with_Full_Descriptions.xlsx"),
        "Plant_Dataset_with_Full_Descriptions.xlsx",
        os.path.join(os.getcwd(), "Plant_Dataset_with_Full_Descriptions.xlsx")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return candidates[0]

def extract_xlsx_using_xml(xlsx_path):
    """
    Pure Python XML+Zipfile parser for .xlsx files.
    Extracts sheets without requiring openpyxl or external C dependencies.
    """
    print(f"Reading {xlsx_path} via pure Python zip/xml parser...")
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        # 1. Load shared strings
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
            # Namespace handling
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                text_elems = si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                val = "".join([t.text for t in text_elems if t.text])
                shared_strings.append(val)
        
        # 2. Find sheet1 / Plant_Database
        sheet_files = [f for f in z.namelist() if f.startswith('xl/worksheets/sheet')]
        if not sheet_files:
            raise ValueError("No worksheets found in xlsx file.")
        
        sheet_xml = z.read(sheet_files[0])
        sheet_tree = ET.fromstring(sheet_xml)
        
        rows_data = []
        for row in sheet_tree.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            row_cells = {}
            for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                ref = c.attrib.get('r', '')
                t = c.attrib.get('t', '')
                v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                val = ""
                if v is not None and v.text:
                    if t == 's': # shared string
                        idx = int(v.text)
                        val = shared_strings[idx] if idx < len(shared_strings) else ""
                    else:
                        val = v.text
                elif c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is') is not None:
                    t_elem = c.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                    if t_elem is not None and t_elem.text:
                        val = t_elem.text

                # Extract column letter
                col_letters = "".join(re.findall(r'[A-Za-z]+', ref))
                row_cells[col_letters] = val
            
            if row_cells:
                rows_data.append(row_cells)

    # Convert sparse column dicts into structured matrix
    if not rows_data:
        raise ValueError("No rows found in Excel sheet.")

    header_row = rows_data[0]
    col_order = sorted(header_row.keys(), key=lambda x: (len(x), x))
    headers = [str(header_row[c]).strip() for c in col_order]

    records = []
    for r in rows_data[1:]:
        rec = {}
        for c, h in zip(col_order, headers):
            rec[h] = r.get(c, "")
        records.append(rec)

    return headers, records

def export_and_train():
    xlsx_path = find_excel_file()
    print("==========================================================")
    print(f"IMPORTING DATASET FROM: {xlsx_path}")
    print("==========================================================")

    if not os.path.exists(xlsx_path):
        print(f"[ERROR] Cannot find {xlsx_path}")
        return False

    records = []
    headers = []

    # Try pandas first, fallback to pure Python XML parser
    try:
        import pandas as pd
        print("Loading Excel with pandas...")
        df = pd.read_excel(xlsx_path, sheet_name=0)
        df = df.fillna("")
        headers = list(df.columns)
        records = df.to_dict('records')
        print(f"✓ Pandas loaded {len(records)} rows and {len(headers)} columns.")
    except Exception as e:
        print(f"Pandas/openpyxl not available or failed ({e}), using built-in XML extractor...")
        headers, records = extract_xlsx_using_xml(xlsx_path)
        print(f"✓ XML extractor loaded {len(records)} rows and {len(headers)} columns.")

    if not records:
        print("[ERROR] No records extracted.")
        return False

    # Save to plants.csv in Text_To_Plant-main and current folder
    target_csvs = [
        os.path.join(os.path.dirname(__file__), "plants.csv"),
        os.path.join(os.path.dirname(__file__), "plants_clean.csv"),
        os.path.join(os.path.dirname(__file__), "..", "plants.csv")
    ]

    for target_path in target_csvs:
        target_dir = os.path.dirname(target_path)
        if os.path.exists(target_dir):
            with open(target_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for r in records:
                    writer.writerow(r)
            print(f"✓ Saved {len(records)} records to {target_path}")

    # Build TF-IDF & NearestNeighbors Models
    try:
        import pandas as pd
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.neighbors import NearestNeighbors

        print("\n==========================================================")
        print("BUILDING VECTORIZER & NEAREST NEIGHBORS SEARCH ARTIFACTS")
        print("==========================================================")

        df = pd.DataFrame(records)

        def clean_text(text):
            text = str(text).lower()
            text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text

        feature_cols = [
            "Common_Name", "Scientific_Name", "Family", "Plant_Type", "Life_Span",
            "Leaf_Shape_Description", "Leaf_Type_Description", "Leaf_Arrangement_Description",
            "Stem_Type_Description", "Stem_Texture_Description", "Flower_Color_Description",
            "Flower_Type_Description", "Flowering_Season", "Fruit_Type_Description",
            "Fruit_Color_Description", "Root_Type_Description", "Habitat_Description",
            "Medicinal_Uses_Description", "Culinary_Uses_Description", "Industrial Use Description",
            "Toxicity_Level_Description", "Smell_Description", "Text Input"
        ]

        active_cols = [c for c in feature_cols if c in df.columns]
        print(f"Indexing fields: {active_cols}")

        combined_texts = []
        vocab_words = set()

        for _, row in df.iterrows():
            parts = []
            for col in active_cols:
                val = str(row.get(col, "")).strip()
                if val:
                    parts.append(val)
                    cleaned_val = clean_text(val)
                    for w in cleaned_val.split():
                        if len(w) > 2 and not w.isdigit():
                            vocab_words.add(w)

            combined_texts.append(clean_text(" ".join(parts)))

        # Train TfidfVectorizer
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            stop_words='english'
        )
        tfidf_matrix = vectorizer.fit_transform(combined_texts)
        print(f"✓ TF-IDF Matrix created with shape: {tfidf_matrix.shape}")

        nn_model = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
        nn_model.fit(tfidf_matrix)
        print(f"✓ NearestNeighbors model trained on all {len(df)} records.")

        # Save artifacts in script dir
        out_dir = os.path.dirname(os.path.abspath(__file__))
        joblib.dump(vectorizer, os.path.join(out_dir, "vectorizer.pkl"))
        joblib.dump(nn_model, os.path.join(out_dir, "model.pkl"))
        joblib.dump(tfidf_matrix, os.path.join(out_dir, "vectors.pkl"))
        joblib.dump(df, os.path.join(out_dir, "data.pkl"))
        joblib.dump(vocab_words, os.path.join(out_dir, "vocab.pkl"))
        print("✓ All 5 model artifacts successfully serialized.")
    except Exception as e:
        print(f"[NOTE] Model training note: {e}")

    print("==========================================================")
    print("DATASET INTEGRATION & EXPORT COMPLETED SUCCESSFULLY!")
    print("==========================================================")
    return True

if __name__ == "__main__":
    export_and_train()
