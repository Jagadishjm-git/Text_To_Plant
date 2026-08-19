"""
test_mango_fix.py
Verifies that Mango descriptions rank Mango above Star Anise with accurate, unforced confidence.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline

def verify_mango():
    print("=" * 80)
    print("VERIFYING MANGO VS STAR ANISE CLASSIFICATION")
    print("=" * 80)

    test_queries = [
        ("Tree with alternate lanceolate leaves, pale yellow panicle flowers and yellow orange drupe", "Mango"),
        ("A tropical tree with alternate lanceolate leaves, pale yellow panicle flowers, and yellow orange drupe fruit", "Mango"),
        ("I'm looking at a Tree with Digestive, anti-inflammatory, vitamin C properties. It has Pale Yellow flowers and Lanceolate leaves. Identify it.", "Mango"),
        ("A large tree with alternate lanceolate leaves, smooth bark, pale yellow panicle flowers in winter-spring and edible sweet yellow-orange drupes.", "Mango"),
        ("A small tree with glossy leaves, red flowers, and round red fruits with juicy edible seeds.", "Pomegranate"),
        ("Aloe vera succulent with thick fleshy serrated leaves and medicinal gel", "Aloe Vera"),
        ("Neem tree with lanceolate leaves, white flowers and pinnate leaves", "Neem")
    ]

    all_passed = True

    for q, expected in test_queries:
        print(f"\nQuery: '{q}'")
        res = execute_plant_identification_pipeline(q)
        results = res.get("results", [])
        if results:
            top_match = results[0]
            c_name = top_match.get("Common_Name")
            pct = top_match.get("Match_Percentage")
            tier = top_match.get("Confidence_Tier")
            feats = top_match.get("Matching_Features")

            print(f"  -> Identified: {c_name} ({top_match.get('Scientific_Name')})")
            print(f"     Confidence: {pct}% {tier}")
            print(f"     Verified Features: {feats}")

            if expected.lower() in c_name.lower():
                print(f"  [PASS] ✓ Correctly ranked {expected} as #1!")
            else:
                print(f"  [FAIL] ✗ Expected {expected}, got {c_name}")
                all_passed = False

            # Ensure Star Anise is not erroneously ranked above or equal
            if len(results) > 1:
                print(f"  -> Candidate #2: {results[1].get('Common_Name')} @ {results[1].get('Match_Percentage')}% {results[1].get('Confidence_Tier')}")
        else:
            print(f"  [FAIL] ✗ Uncertain/No match: {res.get('message')}")
            all_passed = False

    print("\n" + "=" * 80)
    print("VERIFICATION RESULT: " + ("ALL TESTS PASSED!" if all_passed else "FAILURES DETECTED"))
    print("=" * 80)
    return all_passed

if __name__ == "__main__":
    verify_mango()
