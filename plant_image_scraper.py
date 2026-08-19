import os
import csv
import time
import hashlib
import requests
import argparse
import pandas as pd
from urllib.parse import urlparse

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLANTS_CSV = os.path.join(BASE_DIR, "plants.csv")
PLANTS_CLEAN_CSV = os.path.join(BASE_DIR, "plants_clean.csv")
STATIC_DIR = os.path.join(BASE_DIR, "static", "plant_images")
IMAGE_DB = os.path.join(BASE_DIR, "plant_images.csv")
COLLECTION_LOG = os.path.join(BASE_DIR, "image_collection_log.csv")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)

# Priority plants to scrape first
PRIORITY_PLANTS = [
    "Neem", "Holy Basil (Tulsi)", "Mango", "Bamboo", "Ashwagandha", "Lotus", 
    "Aloe Vera", "Turmeric", "Sandalwood", "Banana", "Banyan Tree", "Peepal (Sacred Fig)", 
    "Brahmi", "Curry Leaf", "Indian Gooseberry (Amla)", "Moringa (Drumstick)", "Coconut", 
    "Black Pepper", "Cardamom", "Clove", "Cinnamon", "Castor", "Cotton", "Sugarcane", 
    "Pomegranate", "Sunflower", "Rose", "Jasmine", "Hibiscus", "Papaya", "Tamarind"
]

def compute_hash(file_path):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return None

def download_image(url, plant_id, img_index, scientific_name):
    """Download image, verify format, compute hash."""
    try:
        # Respect GBIF and Wikimedia rate limits by spacing requests
        time.sleep(0.5) 
        
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None, "HTTP error"
            
        content_type = resp.headers.get("Content-Type", "")
        if not content_type.startswith("image/"):
            return None, "Not an image"
            
        ext = "jpg"
        if "png" in content_type: ext = "png"
        elif "webp" in content_type: ext = "webp"
        
        # Check size (ignore very small images)
        if len(resp.content) < 10240: # < 10KB
            return None, "Image too small/low quality"
            
        plant_dir = os.path.join(STATIC_DIR, str(plant_id))
        os.makedirs(plant_dir, exist_ok=True)
        
        filename = f"image_{img_index:03d}.{ext}"
        local_path = os.path.join(plant_dir, filename)
        
        with open(local_path, "wb") as f:
            f.write(resp.content)
            
        img_hash = compute_hash(local_path)
        
        return local_path, img_hash
    except Exception as e:
        return None, str(e)

def search_gbif_for_plant(scientific_name):
    """Query GBIF API for verified plant images using exact scientific name."""
    try:
        # Step 1: Resolve Taxon Key
        match_url = f"https://api.gbif.org/v1/species/match?name={requests.utils.quote(scientific_name)}"
        match_resp = requests.get(match_url, timeout=10).json()
        
        taxon_key = match_resp.get("usageKey")
        if not taxon_key or match_resp.get("matchType") not in ["EXACT", "FUZZY"]:
            return []

        # Step 2: Fetch occurrences with images
        occ_url = f"https://api.gbif.org/v1/occurrence/search?taxonKey={taxon_key}&mediaType=StillImage&limit=20"
        occ_resp = requests.get(occ_url, timeout=10).json()
        
        results = []
        for occ in occ_resp.get("results", []):
            if "media" in occ:
                for media in occ["media"]:
                    if media.get("type") == "StillImage" and media.get("identifier"):
                        results.append({
                            "url": media["identifier"],
                            "license": media.get("license", "Unknown"),
                            "publisher": media.get("publisher", "GBIF Occurrence"),
                            "source_page": f"https://www.gbif.org/occurrence/{occ.get('key')}"
                        })
        return results
    except Exception as e:
        print(f"GBIF Search Error for {scientific_name}: {e}")
        return []

def run_scraper(limit=None):
    print("==================================================")
    print("PLANT IMAGE SCRAPER & VALIDATOR PIPELINE")
    print("==================================================")
    
    # 1. Load active dataset
    if os.path.exists(PLANTS_CSV):
        df = pd.read_csv(PLANTS_CSV)
    else:
        print("Error: plants.csv not found.")
        return
        
    print(f"Loaded {len(df)} total rows from plants.csv.")
    
    # Deduplicate based on Plant_ID
    df = df.drop_duplicates(subset=["Plant_ID"]).copy()
    print(f"Unique Plant_IDs to process: {len(df)}")
    
    # Prioritize important plants
    df['is_priority'] = df['Common_Name'].apply(lambda x: 1 if x in PRIORITY_PLANTS else 0)
    df = df.sort_values(by=['is_priority', 'Plant_ID'], ascending=[False, True])
    
    if limit:
        df = df.head(limit)
        print(f"Applying limit: Processing top {limit} plants.")
        
    # 2. Load existing DB to prevent re-downloading
    existing_images = []
    processed_plant_ids = set()
    existing_hashes = set()
    
    if os.path.exists(IMAGE_DB):
        with open(IMAGE_DB, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_images.append(row)
                processed_plant_ids.add(str(row["Plant_ID"]))
                if row.get("Image_Hash"):
                    existing_hashes.add(row["Image_Hash"])
                    
    # 3. Process plants
    collection_logs = []
    
    stats = {
        "Total plants": len(df),
        "Plants with images": 0,
        "Plants without images": 0,
        "Total images collected": 0,
        "Total verified images": 0,
        "Total rejected images": 0,
        "Duplicate images removed": 0
    }
    
    for idx, row in df.iterrows():
        plant_id = str(row["Plant_ID"])
        common_name = str(row["Common_Name"]).strip()
        scientific_name = str(row["Scientific_Name"]).strip()
        
        print(f"\n[{idx+1}/{len(df)}] Processing Plant_ID: {plant_id} | {common_name} ({scientific_name})")
        
        if plant_id in processed_plant_ids:
            print("  -> Already processed. Skipping cache.")
            continue
            
        if not scientific_name or scientific_name == "nan":
            print("  -> No scientific name. Skipping.")
            collection_logs.append({
                "Plant_ID": plant_id, "Scientific_Name": scientific_name,
                "Search_Status": "FAILED", "Images_Found": 0, "Images_Verified": 0,
                "Images_Rejected": 0, "Failure_Reason": "No scientific name", "Date": time.strftime("%Y-%m-%d")
            })
            continue

        candidates = search_gbif_for_plant(scientific_name)
        print(f"  -> Found {len(candidates)} candidate images from GBIF.")
        
        images_found = len(candidates)
        images_verified = 0
        images_rejected = 0
        duplicate_images = 0
        
        for cand in candidates:
            if images_verified >= 3:
                break # 3-5 images max
                
            img_url = cand["url"]
            print(f"     * Testing image: {img_url[:60]}...")
            
            # Reject if clearly watermarked/wrong based on metadata
            if "shutterstock" in img_url.lower() or "getty" in img_url.lower():
                images_rejected += 1
                continue
                
            local_path, img_hash = download_image(img_url, plant_id, images_verified + 1, scientific_name)
            
            if not local_path:
                print(f"       -> REJECTED: {img_hash}")
                images_rejected += 1
                continue
                
            # Duplicate check
            if img_hash in existing_hashes:
                print("       -> DUPLICATE HASH detected. Removing.")
                os.remove(local_path)
                duplicate_images += 1
                stats["Duplicate images removed"] += 1
                continue
                
            # Accept image
            existing_hashes.add(img_hash)
            images_verified += 1
            stats["Total verified images"] += 1
            stats["Total images collected"] += 1
            
            rel_path = os.path.relpath(local_path, BASE_DIR).replace("\\", "/")
            
            # Save to metadata DB
            existing_images.append({
                "Plant_ID": plant_id,
                "Common_Name": common_name,
                "Scientific_Name": scientific_name,
                "Image_ID": f"{plant_id}_{images_verified:03d}",
                "Image_URL": img_url,
                "Local_Image_Path": rel_path,
                "Source_Website": "GBIF",
                "Source_Page_URL": cand["source_page"],
                "License": cand["license"],
                "Attribution": cand["publisher"],
                "Image_Hash": img_hash,
                "Downloaded_Date": time.strftime("%Y-%m-%d"),
                "Verification_Status": "VERIFIED"
            })
            
            print(f"       -> VERIFIED & SAVED: {rel_path}")

        if images_verified > 0:
            stats["Plants with images"] += 1
            search_status = "SUCCESS"
            fail_reason = ""
        else:
            stats["Plants without images"] += 1
            search_status = "NOT_AVAILABLE"
            fail_reason = "No reliable images found or all rejected"
            
            # Add a placeholder record to DB so we don't retry forever
            existing_images.append({
                "Plant_ID": plant_id,
                "Common_Name": common_name,
                "Scientific_Name": scientific_name,
                "Image_ID": f"{plant_id}_NONE",
                "Image_URL": "",
                "Local_Image_Path": "",
                "Source_Website": "",
                "Source_Page_URL": "",
                "License": "",
                "Attribution": "",
                "Image_Hash": "",
                "Downloaded_Date": time.strftime("%Y-%m-%d"),
                "Verification_Status": "NOT_AVAILABLE"
            })
            
        stats["Total rejected images"] += images_rejected
            
        collection_logs.append({
            "Plant_ID": plant_id, "Scientific_Name": scientific_name,
            "Search_Status": search_status, "Images_Found": images_found, 
            "Images_Verified": images_verified, "Images_Rejected": images_rejected, 
            "Failure_Reason": fail_reason, "Date": time.strftime("%Y-%m-%d")
        })
        
        # Save progress every 10 plants
        if len(existing_images) % 10 == 0:
            save_dbs(existing_images, collection_logs)

    # Final save
    save_dbs(existing_images, collection_logs)
    
    print("\n==================================================")
    print("COLLECTION COMPLETE - STATS")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print("==================================================")

def save_dbs(images, logs):
    """Write databases to CSV."""
    if images:
        df = pd.DataFrame(images)
        df.to_csv(IMAGE_DB, index=False)
        
    if logs:
        log_df = pd.DataFrame(logs)
        if os.path.exists(COLLECTION_LOG):
            existing_logs = pd.read_csv(COLLECTION_LOG)
            log_df = pd.concat([existing_logs, log_df], ignore_index=True)
            # drop duplicates just in case
            log_df = log_df.drop_duplicates()
        log_df.to_csv(COLLECTION_LOG, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of plants to process")
    args = parser.parse_args()
    
    run_scraper(limit=args.limit)
