"""
Quick pipeline validation test.
Tests all major scenarios: specific plants, generic descriptions, fake inputs.
"""
import json
import sys
sys.path.insert(0, '.')

from botanical_pipeline import execute_plant_identification_pipeline

TESTS = [
    # (description, expected_plant_or_UNCERTAIN)
    ("Turmeric perennial herb with rhizome roots and pale yellow spike flowers in tropical moist forests", "Turmeric"),
    ("Neem tree with lanceolate leaves and white panicle flowers antibacterial", "Neem"),
    ("Aquatic herb found in ponds with floating leaf arrangement and orbicular leaf shape pink solitary flowers", "Lotus"),
    ("Aloe vera succulent herb with lanceolate serrated leaves gel skin healing burns laxative", "Aloe Vera"),
    ("Holy Basil Tulsi aromatic herb opposite ovate leaves purple spike flowers respiratory", "Holy Basil (Tulsi)"),
    ("Pomegranate", "Pomegranate"),
    ("Bamboo grass with woody culm jointed culm smooth stems", "Bamboo"),
    ("Coconut palm tree with linear compound pinnate leaves fibrous root tropical coastal", "Coconut"),
    ("Lotus aquatic herb with floating orbicular leaves pink solitary flowers rhizome root ponds", "Lotus"),
    ("Mango tree with lanceolate leaves pale yellow panicle flowers taproot tropical forests", "Mango"),
    # Should be UNCERTAIN
    ("green leaves medicinal tree tropical", "UNCERTAIN"),
    ("laptop charger 65W electronics", "UNCERTAIN"),
    ("big tall yellow plant nice smell good", "UNCERTAIN"),
    ("xyzabc qwerty123", "UNCERTAIN"),
]

print("=" * 65)
print("PLANT IDENTIFICATION PIPELINE - VALIDATION TEST")
print("=" * 65)

passes = 0
for desc, expected in TESTS:
    res = execute_plant_identification_pipeline(desc)
    if res.get("is_plant"):
        plant = res["results"][0]
        actual = plant["Common_Name"]
        conf = plant["Match_Percentage"]
        img_url = plant.get("Photo_Url")
        img_verified = plant.get("Is_Verified_Image", False)
        # Check pass
        ok = (expected != "UNCERTAIN") and (expected.lower() in actual.lower() or actual.lower() in expected.lower())
        status = "PASS" if ok else "FAIL"
        img_ok = "YES" if img_url and img_verified else ("UPLOADED" if img_url else "NONE")
        print(f"[{status}] Expected={expected:30s} Got={actual:30s} Conf={conf:3d}% Img={img_ok}")
    else:
        actual = "UNCERTAIN"
        ok = (expected == "UNCERTAIN")
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] Expected={expected:30s} Got=UNCERTAIN                      Conf=--- Img=N/A")
    if ok:
        passes += 1

print("=" * 65)
print(f"SCORE: {passes}/{len(TESTS)} tests PASSED")
print("=" * 65)
