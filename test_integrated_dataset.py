"""
test_integrated_dataset.py
Verifies characteristic plant description matching on the 10,454-record dataset.
Tests queries where the plant common name is NOT mentioned in the text.
"""

import sys
import os
import json

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline

def test_characteristic_queries():
    print("==========================================================")
    print("TESTING CHARACTERISTIC-BASED PLANT IDENTIFICATION")
    print("==========================================================")

    test_queries = [
        {
            "id": 1,
            "description": "A small tree with glossy leaves, red flowers, and round red fruits.",
            "expected_plant": "Pomegranate",
            "notes": "Pomegranate trait description without common name mention"
        },
        {
            "id": 2,
            "description": "Succulent Herb with Yellow flowers and Rosette Lanceolate leaves for skin healing and burns.",
            "expected_plant": "Aloe Vera",
            "notes": "Aloe Vera trait description"
        },
        {
            "id": 3,
            "description": "Tree with Lanceolate leaves and White flowers in a Tropical/Subtropical dry forests area with antibacterial properties.",
            "expected_plant": "Neem",
            "notes": "Neem trait description"
        },
        {
            "id": 4,
            "description": "Herb with Respiratory disorders, fever, stress, antibacterial properties with Purple/White flowers and Ovate leaves.",
            "expected_plant": "Holy Basil (Tulsi)",
            "notes": "Holy Basil trait description"
        }
    ]

    passed = 0
    total = len(test_queries)

    for case in test_queries:
        print(f"\n--- [Case #{case['id']}] Input: '{case['description']}' ---")
        print(f"Notes: {case['notes']}")
        res = execute_plant_identification_pipeline(case["description"])

        is_plant = res.get("is_plant")
        results = res.get("results", [])

        if not is_plant or case['id'] == 1:
            debug_cand = res.get("candidates_debug", [])
            print(f"\n[DEBUG TOP 10 CANDIDATES FOR CASE #{case['id']}]:")
            for idx, c in enumerate(debug_cand[:10]):
                print(f"   #{idx+1} {c['common_name']} ({c['scientific_name']}) | CombinedScore: {c['score']*100:.1f}% | VectorSim: {c.get('vector_sim',0)*100:.1f}% | StructScore: {c.get('struct_score',0)*100:.1f}%")
                print(f"        Matching: {c['matching_features']}")

        if is_plant and results:
            top_match = results[0]
            matched_name = top_match.get("Common_Name", "")
            confidence = top_match.get("Match_Percentage", 0)
            reasoning = top_match.get("Ai_Explanation") or top_match.get("Reason")
            
            print(f"[RESULT] Predicted: '{matched_name}' ({confidence}%)")
            print(f"         Scientific: {top_match.get('Scientific_Name')}")
            print(f"         Family: {top_match.get('Family')} | Type: {top_match.get('Plant_Type')}")
            print(f"         Reasoning: {reasoning}")

            if case["expected_plant"].lower() in matched_name.lower():
                print(f"[PASS] Case #{case['id']} correctly matched expected species '{case['expected_plant']}'!")
                passed += 1
            else:
                print(f"[FAIL] Case #{case['id']} predicted '{matched_name}', expected '{case['expected_plant']}'")
        else:
            print(f"[FAIL] Case #{case['id']} returned no matches / UNCERTAIN: {res.get('message')}")

    print("\n==========================================================")
    print(f"CHARACTERISTIC IDENTIFICATION RESULTS: {passed} / {total} PASSED ({passed/total*100:.1f}%)")
    print("==========================================================")
    return passed == total

if __name__ == "__main__":
    test_characteristic_queries()
