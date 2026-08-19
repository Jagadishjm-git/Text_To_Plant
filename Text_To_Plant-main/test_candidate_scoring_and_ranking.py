"""
test_candidate_scoring_and_ranking.py
Automated Verification for Candidate-Specific Scoring, Exact Name Isolation, and Margin Calibration.
Tests the 10 critical user test cases and prints candidate-specific scores before and after.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline, get_db_engine
from main import is_fake_or_invalid_plant_query

def run_candidate_scoring_tests():
    print("=" * 85)
    print("🌿 INDEPENDENT CANDIDATE SCORING & INTELLIGENT RANKING VERIFICATION")
    print("=" * 85)

    test_matrix = [
        # (ID, Query Text, Expected Target, Expected Count, Expected Status)
        (1, "Pomegranate", "Pomegranate", 1, "EXACT_NAME"),
        (2, "Pomegranate Tree", "Pomegranate", 1, "EXACT_NAME"),
        (3, "Aloe Vera", "Aloe Vera", 1, "EXACT_NAME"),
        (4, "Neem Tree", "Neem", 1, "EXACT_NAME"),
        (5, "Turmeric", "Turmeric", 1, "EXACT_NAME"),
        (6, "A small tree with glossy leaves, red flowers, and round red fruits.", "Pomegranate", 1, "TRAIT_MATCH"),
        (7, "green leaves medicinal tree", "UNCERTAIN", 0, "UNCERTAIN"),
        (8, "Laptop charger 65W", "REJECTED", 0, "REJECTED"),
        (9, "asdfghjkl 123", "REJECTED", 0, "REJECTED"),
        (10, "tropical plant with green leaves", "UNCERTAIN", 0, "UNCERTAIN")
    ]

    all_passed = True

    for test_id, query_text, expected_target, expected_count, test_type in test_matrix:
        print(f"\n--- Test #{test_id}: '{query_text}' ---")

        if test_type == "REJECTED":
            is_fake = is_fake_or_invalid_plant_query(query_text)
            if is_fake:
                print(f"[PASS] ❌ Correctly Rejected Non-Plant/Hardware input (is_plant: False)")
            else:
                res = execute_plant_identification_pipeline(query_text)
                if not res.get("is_plant"):
                    print(f"[PASS] ❌ Correctly Intercepted by Guardrail (is_plant: False)")
                else:
                    print(f"[FAIL] Should reject non-plant '{query_text}', got: {res}")
                    all_passed = False

        elif test_type == "UNCERTAIN":
            res = execute_plant_identification_pipeline(query_text)
            status = res.get("status")
            if status == "UNCERTAIN" or not res.get("is_plant"):
                print(f"[PASS] ⚠️ Correctly Flagged as UNCERTAIN (Results Count: {len(res.get('results', []))})")
                print(f"       Message: {res.get('message')}")
            else:
                print(f"[FAIL] Should be UNCERTAIN for generic query '{query_text}', got: {res.get('results')}")
                all_passed = False

        elif test_type == "EXACT_NAME":
            res = execute_plant_identification_pipeline(query_text)
            results = res.get("results", [])
            count = len(results)
            top = results[0] if count > 0 else {}
            pred_name = top.get("Common_Name", "")
            pct = top.get("Match_Percentage", 0)
            tier = top.get("Confidence_Tier", "")

            print(f"Results Count: {count} (Expected: {expected_count})")
            for idx, r in enumerate(results, 1):
                print(f"  #{idx} {r.get('Common_Name')} ({r.get('Scientific_Name')}) -> {r.get('Match_Percentage')}% {r.get('Confidence_Tier')}")
                print(f"      Verified: {r.get('Matching_Features')}")

            if count == expected_count and expected_target.lower() in pred_name.lower() and pct >= 90:
                print(f"[PASS] 🌱 Exact Single Match Verified: {pred_name} @ {pct}% {tier} (1 result only, no unrelated padding)")
            else:
                print(f"[FAIL] Expected exactly 1 match '{expected_target}' >= 90%, got count={count}, name={pred_name}, pct={pct}%")
                all_passed = False

        elif test_type == "TRAIT_MATCH":
            res = execute_plant_identification_pipeline(query_text)
            results = res.get("results", [])
            count = len(results)
            top = results[0] if count > 0 else {}
            pred_name = top.get("Common_Name", "")
            pct = top.get("Match_Percentage", 0)
            tier = top.get("Confidence_Tier", "")

            print(f"Results Count: {count} (1-2 Intelligent Limit)")
            for idx, r in enumerate(results, 1):
                print(f"  #{idx} {r.get('Common_Name')} ({r.get('Scientific_Name')}) -> {r.get('Match_Percentage')}% {r.get('Confidence_Tier')}")
                print(f"      Verified: {r.get('Matching_Features')}")

            if expected_target.lower() in pred_name.lower() and pct >= 90 and count <= 2:
                # Check if second candidate is NOT inflated to 95%
                if count > 1 and results[1].get("Match_Percentage") >= 90:
                    print(f"[FAIL] Candidate #2 '{results[1].get('Common_Name')}' was artificially boosted to {results[1].get('Match_Percentage')}%!")
                    all_passed = False
                else:
                    print(f"[PASS] 🌱 Trait Match Verified: Top candidate {pred_name} @ {pct}% {tier} with distinct independent scores.")
            else:
                print(f"[FAIL] Expected top match '{expected_target}' >= 90%, got: {pred_name} @ {pct}%")
                all_passed = False

    print("\n" + "=" * 85)
    print("FINAL TEST OUTCOME: " + ("ALL 10 SCENARIOS PASSED 100%!" if all_passed else "SOME TESTS FAILED"))
    print("=" * 85)
    return all_passed

if __name__ == "__main__":
    success = run_candidate_scoring_tests()
    sys.exit(0 if success else 1)
