import sys
import os
import csv
import json
import re
import urllib.request
import urllib.parse
import ssl

# SSL context for online image/description fetching
ssl_ctx = ssl._create_unverified_context()

PLANTS_CSV_PATH = os.path.join(os.path.dirname(__file__), 'plants.csv')

# Dynamic High-Quality Botanical Photo Sources
PLANT_PHOTO_DATABASE = {
    "neem": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=800&q=80",
    "pomegranate": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=800&q=80",
    "holy basil": "https://images.unsplash.com/photo-1618160702438-9b02ab6515c9?auto=format&fit=crop&w=800&q=80",
    "tulsi": "https://images.unsplash.com/photo-1618160702438-9b02ab6515c9?auto=format&fit=crop&w=800&q=80",
    "aloe vera": "https://images.unsplash.com/photo-1596547609652-9cf5d8d76921?auto=format&fit=crop&w=800&q=80",
    "mango": "https://images.unsplash.com/photo-1553279768-865429fa0078?auto=format&fit=crop&w=800&q=80",
    "turmeric": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=800&q=80",
    "sandalwood": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=800&q=80",
    "bamboo": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=800&q=80",
    "sunflower": "https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=800&q=80",
    "rose": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=800&q=80",
    "coconut": "https://images.unsplash.com/photo-1543637989-b59074092b15?auto=format&fit=crop&w=800&q=80"
}

def clean_text(text):
    return re.sub(r'[^a-z0-9\s]', '', str(text).lower()).strip()

def search_plant_dataset(query):
    query_clean = clean_text(query)
    matches = []
    
    if not os.path.exists(PLANTS_CSV_PATH):
        return matches

    with open(PLANTS_CSV_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            c_name = clean_text(row.get('Common_Name', ''))
            s_name = clean_text(row.get('Scientific_Name', ''))
            
            score = 0
            if query_clean in c_name or c_name in query_clean:
                score += 100
            elif query_clean in s_name or s_name in query_clean:
                score += 90
            else:
                words = [w for w in query_clean.split() if len(w) > 2]
                for w in words:
                    if w in c_name or w in s_name or w in clean_text(row.get('Text Input', '')):
                        score += 30
            
            if score > 0:
                matches.append((score, row))
                
    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:5]]

def fetch_plant_image_url(common_name, scientific_name=""):
    c_clean = clean_text(common_name)
    for key, url in PLANT_PHOTO_DATABASE.items():
        if key in c_clean or c_clean in key:
            return url
            
    # Fallback to Unsplash Source / LoremFlickr Botanical Stream
    query = scientific_name if scientific_name else common_name
    encoded = urllib.parse.quote(query)
    return f"https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?auto=format&fit=crop&w=800&q=80"

def get_complete_plant_profile(query, user_api_key=None):
    results = search_plant_dataset(query)
    if not results:
        return {"found": False, "query": query, "message": "No matching plant found in database."}

    p = results[0]
    c_name = p.get('Common_Name', 'Unknown')
    s_name = p.get('Scientific_Name', 'N/A')
    
    photo_url = fetch_plant_image_url(c_name, s_name)

    profile = {
        "found": True,
        "Common_Name": c_name,
        "Scientific_Name": s_name,
        "Family": p.get('Family', 'N/A'),
        "Kingdom": p.get('Kingdom', 'Plantae'),
        "Class": p.get('Class', 'N/A'),
        "Order": p.get('Order', 'N/A'),
        "Plant_Type": p.get('Plant_Type', 'N/A'),
        "Life_Span": p.get('Life_Span', 'Perennial'),
        "Leaf_Type": p.get('Leaf_Type_Description', 'N/A'),
        "Leaf_Arrangement": p.get('Leaf_Arrangement_Description', 'N/A'),
        "Leaf_Shape": p.get('Leaf_Shape_Description', 'N/A'),
        "Stem_Type": p.get('Stem_Type_Description', 'N/A'),
        "Stem_Texture": p.get('Stem_Texture_Description', 'N/A'),
        "Flower_Color": p.get('Flower_Color_Description', 'N/A'),
        "Flower_Type": p.get('Flower_Type_Description', 'N/A'),
        "Flowering_Season": p.get('Flowering_Season', 'N/A'),
        "Fruit_Type": p.get('Fruit_Type_Description', 'N/A'),
        "Fruit_Color": p.get('Fruit_Color_Description', 'N/A'),
        "Root_Type": p.get('Root_Type_Description', 'N/A'),
        "Habitat": p.get('Habitat_Description', 'N/A'),
        "Native_Region_India": p.get('Native_Region_India', 'N/A'),
        "Medicinal_Uses": p.get('Medicinal_Uses_Description', 'N/A'),
        "Culinary_Uses": p.get('Culinary_Uses_Description', 'N/A'),
        "Industrial_Uses": p.get('Industrial Use Description', 'N/A'),
        "Toxicity_Level": p.get('Toxicity_Level_Description', 'Low'),
        "Smell_Profile": p.get('Smell_Description', 'N/A'),
        "Botanical_Summary": p.get('Text Input', 'N/A'),
        "Image_URL": photo_url,
        "API_Key_Configured": user_api_key is not None
    }
    return profile

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'Neem'
    key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    
    print(f"=== FETCHING PLANT PROFILE FOR: '{target}' ===")
    res = get_complete_plant_profile(target, user_api_key=key)
    print(json.dumps(res, indent=2))
