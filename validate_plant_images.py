import os
import csv
import pandas as pd
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLANTS_CSV = os.path.join(BASE_DIR, "plants.csv")
IMAGE_DB = os.path.join(BASE_DIR, "plant_images.csv")

def validate_images():
    print("==================================================")
    print("VALIDATING PLANT IMAGES DATABASE")
    print("==================================================")

    if not os.path.exists(PLANTS_CSV) or not os.path.exists(IMAGE_DB):
        print("Required CSV files missing.")
        return False

    plants_df = pd.read_csv(PLANTS_CSV)
    valid_ids = set(plants_df["Plant_ID"].astype(str))
    
    images_df = pd.read_csv(IMAGE_DB)
    
    errors = []
    seen_hashes = {}
    
    for idx, row in images_df.iterrows():
        plant_id = str(row["Plant_ID"])
        sci_name = str(row["Scientific_Name"])
        img_id = str(row["Image_ID"])
        local_path = str(row["Local_Image_Path"])
        img_hash = str(row.get("Image_Hash", ""))
        status = str(row["Verification_Status"])
        
        # Check dataset existence
        if plant_id not in valid_ids:
            errors.append(f"Image {img_id} belongs to invalid Plant_ID {plant_id}")
            
        if status == "VERIFIED":
            full_path = os.path.join(BASE_DIR, local_path)
            
            # Check file existence
            if not os.path.exists(full_path):
                errors.append(f"File missing for {img_id}: {local_path}")
            else:
                # Check if it can be opened
                try:
                    with Image.open(full_path) as img:
                        img.verify()
                        if img.width < 100 or img.height < 100:
                            errors.append(f"Image {img_id} is too small ({img.width}x{img.height})")
                except Exception as e:
                    errors.append(f"Image {img_id} is corrupt or invalid: {e}")
            
            # Check duplicate hash logic
            if img_hash:
                if img_hash in seen_hashes:
                    errors.append(f"Duplicate hash detected between {img_id} and {seen_hashes[img_hash]}")
                seen_hashes[img_hash] = img_id
                
            if not row.get("License") or not row.get("Source_Website"):
                errors.append(f"Image {img_id} missing licensing or source metadata")
                
    if not errors:
        print(f"PASS: All {len(images_df)} records validated successfully.")
        print(f"Verified files: {len(seen_hashes)}")
        print("==================================================")
        return True
    else:
        print(f"FAIL: Found {len(errors)} errors:")
        for err in errors:
            print(" -", err)
        print("==================================================")
        return False

if __name__ == "__main__":
    validate_images()
