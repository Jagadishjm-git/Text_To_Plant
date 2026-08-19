"""
benchmark_confidence_scoring.py
Evaluates 25 known botanical species descriptions + generic, fake, and non-plant inputs.
Measures and reports confidence percentages, confidence tiers (HIGH, GOOD, MODERATE, UNCERTAIN, REJECTED),
and verified morphological characteristics.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline, get_db_engine
from main import is_fake_or_invalid_plant_query

def run_benchmark():
    print("=" * 80)
    print("🌿 BOTANICAL CONFIDENCE SCORING & MULTI-SIGNAL HYBRID BENCHMARK SUITE")
    print("=" * 80)

    test_cases = [
        # --- 25 KNOWN BOTANICAL DESCRIPTIONS ---
        ("Pomegranate", "A small tree with glossy leaves, red flowers, and round red fruits with juicy edible seeds."),
        ("Aloe Vera", "Aloe vera succulent with thick fleshy serrated leaves and medicinal gel"),
        ("Neem", "Neem tree with lanceolate leaves, white flowers and pinnate leaves"),
        ("Holy Basil (Tulsi)", "Herb with opposite ovate leaves, purple white spike flowers, and strong aroma"),
        ("Mango", "Tree with alternate lanceolate leaves, pale yellow panicle flowers and yellow orange drupe"),
        ("Bamboo", "Grass with linear lanceolate leaves, woody culm stem and rhizome root"),
        ("Ashwagandha", "Shrub with alternate ovate elliptic leaves, hairy stem, and bell shaped flowers"),
        ("Lotus", "Aquatic herb with floating orbicular leaves, pink white solitary flowers and rhizome root"),
        ("Turmeric", "Herb with oblong lanceolate leaves, pseudostem, spike flowers and rhizome root"),
        ("Sandalwood", "Tree with opposite elliptic leaves, purple red panicle flowers and black drupe"),
        ("Banana", "Herb with spiral oblong leaves, pseudostem, yellow berry and rhizome"),
        ("Banyan Tree", "Tree with ovate leaves, syconium flowers, red fig fruit and prop roots"),
        ("Peepal (Sacred Fig)", "Tree with cordate with drip tip leaves and purple syconium fig fruit"),
        ("Brahmi", "Herb with opposite oblong leaves, white pale violet solitary flowers in wetlands"),
        ("Curry Leaf", "Shrub with compound pinnate leaves, white flowers and black berry fruit"),
        ("Indian Gooseberry (Amla)", "Tree with alternate oblong leaves, green yellow drupe fruit rich in vitamin C"),
        ("Moringa (Drumstick)", "Tree with compound tripinnate leaves, white panicle flowers and capsule pod fruit"),
        ("Coconut", "Palm tree with linear compound pinnate leaves, spadix flowers and green brown drupe"),
        ("Black Pepper", "Climber with alternate ovate leaves, vine climber stem and red black drupe fruit"),
        ("Cardamom", "Herb with alternate lanceolate leaves, pseudostem and green capsule fruit"),
        ("Sunflower", "Herb with alternate ovate leaves, yellow head flowers and achene fruit"),
        ("Hibiscus", "Shrub with alternate ovate leaves, red solitary flowers and capsule fruit"),
        ("Mint", "Herb with opposite ovate leaves, aromatic foliage and purple spike flowers"),
        ("Ginger", "Herb with alternate lanceolate leaves, pseudostem, rhizome root and spicy aroma"),
        ("Clove", "Tree with opposite elliptic leaves, crimson flower buds and drupe fruit"),

        # --- GENERIC AMBIGUOUS INPUTS (Must be UNCERTAIN) ---
        ("GENERIC", "green leaves medicinal tree"),
        ("GENERIC", "tropical plant with green leaves"),

        # --- NON-PLANT & GIBBERISH INPUTS (Must be REJECTED) ---
        ("NON_PLANT", "laptop charger 65W"),
        ("NON_PLANT", "intel core i9 processor 32GB ram"),
        ("GIBBERISH", "asdfghjkl 123")
    ]

    engine = get_db_engine()
    print(f"Total Dataset Records: {len(engine.plants)}")
    print("-" * 80)
    print(f"{'#':<3} | {'Target Species':<24} | {'Result / Status':<22} | {'Score':<6} | {'Tier':<10} | {'Status'}")
    print("-" * 80)

    passed_count = 0
    total_count = len(test_cases)
    high_conf_count = 0

    for idx, (expected_target, query_text) in enumerate(test_cases, 1):
        if expected_target in ["NON_PLANT", "GIBBERISH"]:
            is_fake = is_fake_or_invalid_plant_query(query_text)
            if is_fake:
                print(f"{idx:<3} | {expected_target:<24} | {'REJECTED (Non-Plant)':<22} | {'--':<6} | {'REJECTED':<10} | PASS ✓")
                passed_count += 1
            else:
                res = execute_plant_identification_pipeline(query_text)
                if not res.get("is_plant"):
                    print(f"{idx:<3} | {expected_target:<24} | {'REJECTED (Guardrail)':<22} | {'--':<6} | {'REJECTED':<10} | PASS ✓")
                    passed_count += 1
                else:
                    print(f"{idx:<3} | {expected_target:<24} | {'FAILED (Not Rejected)':<22} | {'--':<6} | {'ERROR':<10} | FAIL ✗")

        elif expected_target == "GENERIC":
            res = execute_plant_identification_pipeline(query_text)
            status = res.get("status")
            if status == "UNCERTAIN" or not res.get("is_plant"):
                print(f"{idx:<3} | {'Generic Ambiguous':<24} | {'UNCERTAIN (Guarded)':<22} | {res.get('confidence', 0):<4}% | {'UNCERTAIN':<10} | PASS ✓")
                passed_count += 1
            else:
                print(f"{idx:<3} | {'Generic Ambiguous':<24} | {'FAILED (Forced Plant)':<22} | {res.get('confidence', 0):<4}% | {res.get('confidence_tier', ''):<10} | FAIL ✗")

        else:
            res = execute_plant_identification_pipeline(query_text)
            results = res.get("results", [])
            predicted = results[0]["Common_Name"] if results else "None"
            pct = results[0]["Match_Percentage"] if results else 0
            tier = results[0]["Confidence_Tier"] if results else "LOW"
            feats = results[0]["Matching_Features"] if results else []

            # Check if expected target matches predicted plant
            matched = res.get("is_plant") and (expected_target.lower() in predicted.lower() or predicted.lower() in expected_target.lower())
            
            if pct >= 90:
                high_conf_count += 1

            status_str = "PASS ✓" if matched and pct >= 75 else ("PASS (MOD) ✓" if matched and pct >= 50 else "FAIL ✗")
            if matched and pct >= 50:
                passed_count += 1

            print(f"{idx:<3} | {expected_target:<24} | {predicted[:20]:<22} | {pct:<4}% | {tier:<10} | {status_str}")

    print("=" * 80)
    print(f"BENCHMARK RESULTS: {passed_count}/{total_count} Passed ({passed_count/total_count*100:.1f}%)")
    print(f"HIGH Confidence (90%+): {high_conf_count}/25 botanical cases ({high_conf_count/25*100:.1f}%)")
    print("=" * 80)

    return passed_count == total_count

if __name__ == "__main__":
    success = run_benchmark()
    sys.exit(0 if success else 1)
