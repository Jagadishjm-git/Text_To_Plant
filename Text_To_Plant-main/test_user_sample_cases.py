"""
test_user_sample_cases.py
Verifies the exact user test matrix against the Botanical Pipeline & Protected API.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, is_fake_or_invalid_plant_query
from botanical_pipeline import execute_plant_identification_pipeline
import db

def test_user_cases():
    print("==========================================================")
    print("TESTING USER BOTANICAL TEST MATRIX")
    print("==========================================================")

    test_matrix = [
        ("A small tree with glossy leaves, red flowers, and round red fruits.", "Pomegranate", True),
        ("A small tree with red flowers and round red fruits like pomegranate", "Pomegranate", True),
        ("Aloe vera succulent with thick fleshy leaves and medicinal gel", "Aloe Vera", True),
        ("Neem tree with pinnate leaves and white flowers", "Neem", True),
        ("green leaves medicinal tree", "UNCERTAIN", False),
        ("laptop charger 65W", "REJECTED_NON_PLANT", False),
        ("asdfghjkl 123", "REJECTED_GIBBERISH", False),
    ]

    all_passed = True

    for text, expected, should_be_positive in test_matrix:
        # Check fake / non-plant guardrails first
        is_invalid = is_fake_or_invalid_plant_query(text)

        if expected in ["REJECTED_NON_PLANT", "REJECTED_GIBBERISH"]:
            if is_invalid:
                print(f"[PASS] ❌ Correctly Rejected Non-Plant/Gibberish: '{text}'")
            else:
                pipe_res = execute_plant_identification_pipeline(text)
                if not pipe_res.get("is_plant") or pipe_res.get("status") == "UNCERTAIN":
                    print(f"[PASS] ❌ Correctly Intercepted as Non-Plant/Uncertain: '{text}'")
                else:
                    print(f"[FAIL] Should reject non-plant '{text}'")
                    all_passed = False
        elif expected == "UNCERTAIN":
            pipe_res = execute_plant_identification_pipeline(text)
            if not pipe_res.get("is_plant") or pipe_res.get("status") == "UNCERTAIN":
                print(f"[PASS] ⚠️ Correctly Flagged as Uncertain (Generic Description): '{text}'")
            else:
                print(f"[FAIL] Should flag as uncertain '{text}', got: {pipe_res}")
                all_passed = False
        else:
            pipe_res = execute_plant_identification_pipeline(text)
            results = pipe_res.get("results", [])
            predicted = results[0]["Common_Name"] if results else "None"
            if pipe_res.get("is_plant") and expected.lower() in predicted.lower():
                print(f"[PASS] 🌱 Identified: '{text[:45]}...' -> {predicted} ({results[0].get('Match_Percentage')}%)")
            else:
                print(f"[FAIL] Expected {expected} for '{text}', got: {predicted}")
                all_passed = False

    print("==========================================================")
    print("ALL USER TEST CASES VERIFIED: " + ("100% MATCH!" if all_passed else "SOME TESTS FAILED"))
    print("==========================================================")
    return all_passed

if __name__ == "__main__":
    test_user_cases()
