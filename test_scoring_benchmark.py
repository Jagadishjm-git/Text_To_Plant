import sys
import json
from botanical_pipeline import execute_plant_identification_pipeline

TEST_CASES = [
    # --- SECTION 1: DETAILED BOTANICAL CHARACTERISTIC DESCRIPTIONS (Target: 90%+ HIGH Confidence) ---
    {
        "id": 1,
        "input": "Aloe vera succulent with thick fleshy serrated leaves and medicinal gel",
        "expected": "Aloe Vera",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 2,
        "input": "Neem tree with lanceolate leaves, white flowers and pinnate leaves",
        "expected": "Neem",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 3,
        "input": "A small tree with glossy leaves, red flowers, and round red fruits.",
        "expected": "Pomegranate",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 4,
        "input": "Herb with Respiratory disorders, fever, stress, antibacterial properties with Purple/White flowers and Ovate leaves.",
        "expected": "Holy Basil (Tulsi)",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 5,
        "input": "Tree with Lanceolate leaves and White flowers in a Tropical/Subtropical dry forests area with antibacterial properties.",
        "expected": "Neem",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 6,
        "input": "Succulent Herb with Yellow flowers and Rosette Lanceolate leaves for skin healing and burns.",
        "expected": "Aloe Vera",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 7,
        "input": "Tree with Simple Alternate Lanceolate leaves, White flowers, and Berry fruit used for digestive health.",
        "expected": "Indian Bael",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 8,
        "input": "Grass with Linear leaves, Greenish Spadix flowers, Fibrous roots, and Grain fruit used for construction.",
        "expected": "Bamboo",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 9,
        "input": "Herb with Ovate leaves, Yellowish-Green flowers, Berry fruit, and Tuberous Taproot used for stress and stamina.",
        "expected": "Ashwagandha",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 10,
        "input": "Tree with Simple Opposite Elliptic leaves, White/Yellow flowers, Drupe fruit, and Taproot used for oral hygiene.",
        "expected": "Meswak",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 11,
        "input": "Tree with Simple Alternate Oblong-Lanceolate leaves, Orange-Red Solitary flowers, Berry fruit, and Taproot for heart health.",
        "expected": "Pomegranate",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 12,
        "input": "Climber with Heart-shaped Cordate leaves, Yellowish-Green Umbel flowers, Berry fruit, and Taproot for immunity.",
        "expected": "Giloy",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 13,
        "input": "Tree with Compound Alternate Lanceolate leaves, White Terminal Cyme flowers, Berry fruit, and Taproot for digestion.",
        "expected": "Curry Leaf",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 14,
        "input": "Tree with Simple Alternate Elliptic leaves, Yellow/White flowers, Fibrous fruit, and Taproot for heart health.",
        "expected": "Arjuna",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 15,
        "input": "Tree with Simple Alternate Cordate leaves, Yellowish flowers, Syconium fruit, and Taproot.",
        "expected": "Peepal",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 16,
        "input": "Tree with Simple Alternate Oblong leaves, Yellow flowers, Pod fruit, and Taproot for skin.",
        "expected": "Red Sandalwood",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 17,
        "input": "Herb with Simple Opposite Serrated leaves, White/Purple flowers, Capsule fruit, and Taproot for memory.",
        "expected": "Brahmi",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 18,
        "input": "Tree with Simple Alternate Lanceolate leaves, Reddish-Purple Cyme flowers, Drupe fruit, and Taproot for fever.",
        "expected": "Sandalwood",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 19,
        "input": "Herb with Pseudostem, White/Purple Raceme flowers, Capsule fruit, and Rhizome root for digestion.",
        "expected": "Cardamom",
        "category": "Known Plant (High Evidence)"
    },
    {
        "id": 20,
        "input": "Tree with Simple Opposite Elliptic leaves and Crimson Corymb flowers used for dental pain relief.",
        "expected": "Clove",
        "category": "Known Plant (High Evidence)"
    },

    # --- SECTION 2: GENERIC / AMBIGUOUS INPUTS (Expected: UNCERTAIN) ---
    {
        "id": 21,
        "input": "green leaves medicinal tree",
        "expected": None,
        "category": "Generic / Ambiguous"
    },
    {
        "id": 22,
        "input": "tropical plant with green leaves",
        "expected": None,
        "category": "Generic / Ambiguous"
    },

    # --- SECTION 3: FAKE / NON-PLANT INPUTS (Expected: REJECTED / NO BOTANICAL SUBJECT) ---
    {
        "id": 23,
        "input": "laptop charger 65W",
        "expected": None,
        "category": "Non-Plant Input"
    },
    {
        "id": 24,
        "input": "magic unicorn dragon leaf 123",
        "expected": None,
        "category": "Fake / Non-Plant Input"
    },
    {
        "id": 25,
        "input": "qwertyuiop asdfghjkl zxcvbnm",
        "expected": None,
        "category": "Gibberish Input"
    }
]

def run_benchmark():
    print("=" * 80)
    print("BENCHMARKING WEIGHTED MULTI-DIMENSIONAL BOTANICAL CONFIDENCE SCORING")
    print("=" * 80)

    passed_count = 0
    total_cases = len(TEST_CASES)

    print(f"{'ID':<4} | {'Input Snippet':<45} | {'Predicted Species':<22} | {'Confidence':<12} | {'Tier':<8} | {'Status'}")
    print("-" * 115)

    for case in TEST_CASES:
        res = execute_plant_identification_pipeline(case["input"])
        is_plant = res.get("is_plant", False)
        status = res.get("status", "UNCERTAIN")
        results = res.get("results", [])

        if is_plant and results:
            top = results[0]
            pred_name = top["Common_Name"]
            confidence = top.get("Match_Percentage", top.get("confidence", 0))
            tier = top.get("Confidence_Tier", "HIGH" if confidence >= 90 else ("GOOD" if confidence >= 75 else "MODERATE"))
        else:
            pred_name = "None / Uncertain"
            confidence = res.get("confidence", 0)
            tier = "UNCERTAIN"

        if case["expected"] is not None:
            # Plant identification test
            exp_words = [w.strip("()").lower() for w in case["expected"].split() if len(w) > 2]
            passed = (is_plant and pred_name and any(w in pred_name.lower() for w in exp_words))
        else:
            # Generic or fake input rejection test
            passed = not is_plant or status == "UNCERTAIN"

        if passed:
            passed_count += 1
            verdict = "[PASS]"
        else:
            verdict = "[FAIL]"

        snippet = (case["input"][:42] + "...") if len(case["input"]) > 45 else case["input"]
        print(f"{case['id']:<4} | {snippet:<45} | {pred_name[:22]:<22} | {confidence}% {' ':<6} | {tier:<8} | {verdict}")

    print("=" * 80)
    print(f"BENCHMARK COMPLETED: {passed_count} / {total_cases} PASSED ({(passed_count / total_cases) * 100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    run_benchmark()
