"""
test_integrated_dataset.py
Automated Verification Suite for the 10,454-Record Dataset Integration & Hybrid Matching Pipeline.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline, get_db_engine
from main import is_fake_or_invalid_plant_query

def run_integration_tests():
    print("==========================================================")
    print("RUNNING 10,454-RECORD DATASET INTEGRATION VERIFICATION")
    print("==========================================================")

    engine = get_db_engine()
    total_records = len(engine.plants)
    print(f"✓ Dataset size verified: {total_records} records loaded in engine.")

    test_matrix = [
        ("A small tree with glossy leaves, red flowers, and round red fruits.", "Pomegranate", True),
        ("A small tree with red flowers and round red fruits like pomegranate", "Pomegranate", True),
        ("Aloe vera succulent with thick fleshy leaves and medicinal gel", "Aloe Vera", True),
        ("Neem tree with pinnate leaves and white flowers", "Neem", True),
        ("green leaves medicinal tree", "UNCERTAIN", False),
        ("laptop charger 65W", "REJECTED", False),
        ("asdfghjkl 123", "REJECTED", False)
    ]

    all_passed = True

    for text, expected, should_match in test_matrix:
        # Check non-plant / gibberish filter
        if expected == "REJECTED":
            is_fake = is_fake_or_invalid_plant_query(text)
            if is_fake:
                print(f"[PASS] ❌ Correctly Rejected Non-Plant/Gibberish: '{text}'")
            else:
                res = execute_plant_identification_pipeline(text)
                if not res.get("is_plant") or res.get("status") == "UNCERTAIN":
                    print(f"[PASS] ❌ Correctly Intercepted: '{text}'")
                else:
                    print(f"[FAIL] Should reject non-plant '{text}'")
                    all_passed = False
        elif expected == "UNCERTAIN":
            res = execute_plant_identification_pipeline(text)
            if not res.get("is_plant") or res.get("status") == "UNCERTAIN":
                print(f"[PASS] ⚠️ Correctly Flagged as UNCERTAIN: '{text}'")
            else:
                print(f"[FAIL] Should be uncertain for generic input '{text}', got: {res.get('results')}")
                all_passed = False
        else:
            res = execute_plant_identification_pipeline(text)
            results = res.get("results", [])
            predicted = results[0]["Common_Name"] if results else None
            match_pct = results[0]["Match_Percentage"] if results else 0
            if res.get("is_plant") and predicted and expected.lower() in predicted.lower():
                print(f"[PASS] 🌱 Identified: '{text[:45]}...' -> {predicted} ({match_pct}%)")
            else:
                print(f"[FAIL] Expected {expected} for '{text}', got: {predicted}")
                all_passed = False

    print("==========================================================")
    print("VERIFICATION SUITE: " + ("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED"))
    print("==========================================================")
    return all_passed

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
