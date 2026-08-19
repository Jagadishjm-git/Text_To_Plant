import os
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DB = os.path.join(BASE_DIR, "plant_images.csv")

_IMAGE_CACHE = None

def load_image_db():
    global _IMAGE_CACHE
    if _IMAGE_CACHE is not None:
        return _IMAGE_CACHE
        
    _IMAGE_CACHE = {}
    if not os.path.exists(IMAGE_DB):
        return _IMAGE_CACHE
        
    with open(IMAGE_DB, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            plant_id = str(row["Plant_ID"])
            if plant_id not in _IMAGE_CACHE:
                _IMAGE_CACHE[plant_id] = []
            
            if row["Verification_Status"] == "VERIFIED":
                # Ensure the path is correct for web serving
                path = row["Local_Image_Path"].replace("\\", "/")
                _IMAGE_CACHE[plant_id].append({
                    "url": f"/{path}",
                    "source": row["Source_Website"],
                    "is_verified": True
                })
                
    return _IMAGE_CACHE

def get_verified_plant_image(common_name, scientific_name="", plant_id=None):
    """
    Returns a verified image dict:
      {url: str, source: str, is_verified: True}
    or if no verified image available:
      {url: None, source: None, is_verified: False}

    Uses Plant_ID as the absolute identity.
    """
    if not plant_id:
        return {"url": None, "source": None, "is_verified": False}
        
    db = load_image_db()
    pid = str(plant_id)
    
    if pid in db and len(db[pid]) > 0:
        # Return the first verified image for this plant
        return db[pid][0]
        
    return {"url": None, "source": None, "is_verified": False}
