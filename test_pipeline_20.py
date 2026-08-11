import sys
import os
import json
from botanical_pipeline import execute_plant_identification_pipeline

# 25 TEST CASES (20 Positive Dataset Cases + 5 Negative / Ambiguous Cases)
TEST_SUITE = [
    # --- POSITIVE TEST CASES FROM DATASET ---
    {
        "id": 1,
        "input": "I found a Tree with Lanceolate leaves and White flowers in a Tropical/Subtropical dry forests area.",
        "expected_plant": "Neem",
        "should_be_confident": True
    },
    {
        "id": 2,
        "input": "Herb with Respiratory disorders, fever, stress, antibacterial properties. It has Purple/White flowers and Ovate leaves.",
        "expected_plant": "Holy Basil (Tulsi)",
        "should_be_confident": True
    },
    {
        "id": 3,
        "input": "I'm looking at a Tree with Digestive, anti-inflammatory, vitamin C properties. It has Pale Yellow flowers and Lanceolate leaves.",
        "expected_plant": "Mango",
        "should_be_confident": True
    },
    {
        "id": 4,
        "input": "Grass that has Smooth stems and Spikelet flowers with Woody Culm. It grows in Tropical forests, river banks with Rhizome roots.",
        "expected_plant": "Bamboo",
        "should_be_confident": True
    },
    {
        "id": 5,
        "input": "Shrub that has Hairy stems and Bell-shaped flowers. It grows in Dry/Subtropical regions used as adaptogen and stress tonic.",
        "expected_plant": "Ashwagandha",
        "should_be_confident": True
    },
    {
        "id": 6,
        "input": "Aquatic Herb found in Ponds, lakes, wetlands with Floating arrangement and Aggregate fruits and Orbicular leaves.",
        "expected_plant": "Lotus",
        "should_be_confident": True
    },
    {
        "id": 7,
        "input": "Succulent Herb with Yellow flowers and Rosette Lanceolate leaves for skin healing and burns.",
        "expected_plant": "Aloe Vera",
        "should_be_confident": True
    },
    {
        "id": 8,
        "input": "Herb that has Smooth stems and Spike flowers with Rhizome root. Spice used as anti-inflammatory antioxidant.",
        "expected_plant": "Turmeric",
        "should_be_confident": True
    },
    {
        "id": 9,
        "input": "Tree with Elliptic leaves and Purple/Red flowers in a Tropical dry deciduous forests area with fragrant sandalwood scent.",
        "expected_plant": "Sandalwood",
        "should_be_confident": True
    },
    {
        "id": 10,
        "input": "Herb with Pseudostem, White/Cream flowers and Oblong leaves used for potassium and digestive health.",
        "expected_plant": "Banana",
        "should_be_confident": True
    },
    {
        "id": 11,
        "input": "Tree with aerial prop roots, Ovate leaves, and Syconium flowers in villages.",
        "expected_plant": "Banyan Tree",
        "should_be_confident": True
    },
    {
        "id": 12,
        "input": "Tree with Cordate leaves with drip tip and Syconium flowers used for asthma and diabetes.",
        "expected_plant": "Peepal (Sacred Fig)",
        "should_be_confident": True
    },
    {
        "id": 13,
        "input": "Herb with Memory enhancer properties, White/Pale Violet Solitary flowers and Oblong leaves in wetlands.",
        "expected_plant": "Brahmi",
        "should_be_confident": True
    },
    {
        "id": 14,
        "input": "Shrub/Small Tree with Compound Pinnate Alternate Lanceolate leaves and White Corymb flowers used as flavoring in curries.",
        "expected_plant": "Curry Leaf",
        "should_be_confident": True
    },
    {
        "id": 15,
        "input": "Tree found in Tropical dry forests with Drupe fruits and Alternate arrangement high in Vitamin C.",
        "expected_plant": "Indian Gooseberry (Amla)",
        "should_be_confident": True
    },
    {
        "id": 16,
        "input": "Tree with Compound Tripinnate Alternate Ovate leaves, White/Cream Panicle flowers, and Capsule Pod fruits.",
        "expected_plant": "Moringa (Drumstick)",
        "should_be_confident": True
    },
    {
        "id": 17,
        "input": "Palm Tree with Linear leaves, Pale Yellow Spadix flowers, and Fibrous coastal roots.",
        "expected_plant": "Coconut",
        "should_be_confident": True
    },
    {
        "id": 18,
        "input": "Perennial Climber with Vine climber stems, Ovate leaves, and Adventitious roots used as spice.",
        "expected_plant": "Black Pepper",
        "should_be_confident": True
    },
    {
        "id": 19,
        "input": "Herb with Pseudostem, White/Purple Raceme flowers, Capsule fruits, and Rhizome root in moist forests.",
        "expected_plant": "Cardamom",
        "should_be_confident": True
    },
    {
        "id": 20,
        "input": "Tree with Simple Opposite Elliptic leaves and Crimson Corymb flowers used for dental pain relief.",
        "expected_plant": "Clove",
        "should_be_confident": True
    },

    # --- NEGATIVE / AMBIGUOUS / FAKE TEST CASES (MUST RETURN UNCERTAIN) ---
    {
        "id": 21,
        "input": "green leaves medicinal tree",
        "expected_plant": None,
        "should_be_confident": False
    },
    {
        "id": 22,
        "input": "tropical plant with green leaves",
        "expected_plant": None,
        "should_be_confident": False
    },
    {
        "id": 23,
        "input": "magic unicorn dragon leaf 123",
        "expected_plant": None,
        "should_be_confident": False
    },
    {
        "id": 24,
        "input": "laptop charger with 65W cable",
        "expected_plant": None,
        "should_be_confident": False
    },
    {
        "id": 25,
        "input": "qwertyuiop asdfghjkl zxcvbnm",
        "expected_plant": None,
        "should_be_confident": False
    }
]

def run_all_tests():
    print("==========================================================")
    print("RUNNING 25-CASE BOTANICAL PIPELINE VERIFICATION SUITE")
    print("==========================================================")

    passed_count = 0
    total_count = len(TEST_SUITE)

    for test in TEST_SUITE:
        t_id = test["id"]
        inp = test["input"]
        exp = test["expected_plant"]
        should_conf = test["should_be_confident"]

        res = execute_plant_identification_pipeline(inp)
        is_plant = res.get("is_plant", False)
        status = res.get("status", "UNCERTAIN")
        results = res.get("results", [])

        predicted = results[0]["Common_Name"] if results else None
        confidence = res.get("confidence", 0)

        pass_status = False
        if should_conf:
            if is_plant and status == "CONFIDENT" and predicted and exp and exp.lower() in predicted.lower():
                pass_status = True
        else:
            if not is_plant or status == "UNCERTAIN" or predicted is None:
                pass_status = True

        if pass_status:
            passed_count += 1
            print(f"[PASS] Case #{t_id:02d}: '{inp[:40]}...' -> Predicted: '{predicted}' ({confidence}%) | Expected: '{exp}'")
        else:
            print(f"[FAIL] Case #{t_id:02d}: '{inp}' -> Predicted: '{predicted}' ({confidence}%) | Expected: '{exp}' | Status: {status}")

    print("==========================================================")
    print(f"AUTOMATED SUITE RESULTS: {passed_count} / {total_count} PASSED ({passed_count/total_count*100:.1f}%)")
    print("==========================================================")
    return passed_count == total_count

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
