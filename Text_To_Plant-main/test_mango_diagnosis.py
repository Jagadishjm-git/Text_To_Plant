"""
test_mango_diagnosis.py
Diagnoses why Mango was misclassified as Star Anise and tests the fix.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline, get_db_engine, extract_botanical_features

def test_mango_queries():
    engine = get_db_engine()
    
    # Check Mango and Star Anise rows in dataset
    mango_row = engine.common_name_map.get("mango")
    star_anise_row = engine.common_name_map.get("star anise")
    
    print("==================================================")
    print("DATASET CHECK:")
    print(f"Mango row: {mango_row.get('Common_Name') if mango_row else 'NOT FOUND'} ({mango_row.get('Scientific_Name') if mango_row else ''})")
    if mango_row:
        print(f"   Leaf: {mango_row.get('Leaf_Shape_Description')}, Flower: {mango_row.get('Flower_Color_Description')}, Fruit: {mango_row.get('Fruit_Type_Description')} ({mango_row.get('Fruit_Color_Description')})")
        print(f"   Plant Type: {mango_row.get('Plant_Type')}, Habitat: {mango_row.get('Habitat_Description')}")
        print(f"   Text Input: {mango_row.get('Text Input')}")
    
    print(f"Star Anise row: {star_anise_row.get('Common_Name') if star_anise_row else 'NOT FOUND'} ({star_anise_row.get('Scientific_Name') if star_anise_row else ''})")
    if star_anise_row:
        print(f"   Leaf: {star_anise_row.get('Leaf_Shape_Description')}, Flower: {star_anise_row.get('Flower_Color_Description')}, Fruit: {star_anise_row.get('Fruit_Type_Description')} ({star_anise_row.get('Fruit_Color_Description')})")
        print(f"   Text Input: {star_anise_row.get('Text Input')}")

    print("==================================================")
    
    test_queries = [
        "Tree with alternate lanceolate leaves, pale yellow panicle flowers and yellow orange drupe",
        "A tropical tree with alternate lanceolate leaves, pale yellow panicle flowers, and yellow orange drupe fruit",
        "Tree with lanceolate leaves, pale yellow flowers, and drupe fruit",
        "I'm looking at a Tree with Digestive, anti-inflammatory, vitamin C properties. It has Pale Yellow flowers and Lanceolate leaves. Identify it.",
        "A large tree with alternate lanceolate leaves, smooth bark, pale yellow panicle flowers in winter-spring and edible sweet yellow-orange drupes."
    ]

    for q in test_queries:
        print(f"\nQUERY: '{q}'")
        res = execute_plant_identification_pipeline(q)
        results = res.get("results", [])
        if results:
            for idx, r in enumerate(results[:3], 1):
                print(f"   #{idx} {r.get('Common_Name')} ({r.get('Scientific_Name')}) -> {r.get('Match_Percentage')}% {r.get('Confidence_Tier')}")
                print(f"        Verified: {r.get('Matching_Features')}")
        else:
            print(f"   Result: {res.get('status')} - {res.get('message')}")

if __name__ == "__main__":
    test_mango_queries()
