import sys
import os

from botanical_pipeline import execute_plant_identification_pipeline

TEST_QUERIES = [
    "Pomegranate",
    "Pomegranate Tree",
    "Aloe Vera",
    "Neem Tree",
    "Turmeric",
    "A small tree with glossy leaves, red flowers, and round red fruits.",
    "green leaves medicinal tree",
    "Laptop charger 65W",
    "qwertyuiop asdfghjkl zxcvbnm",
    "tree with green leaves and small white flowers"
]

def main():
    print("=" * 80)
    print("RUNNING 10 USER-REQUESTED TEST SCENARIOS FOR CANDIDATE-SPECIFIC CONFIDENCE SCORING")
    print("=" * 80)

    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"\n--- TEST #{i}: '{q}' ---")
        res = execute_plant_identification_pipeline(q)
        is_plant = res.get("is_plant", False)
        status = res.get("status", "UNCERTAIN")
        results = res.get("results", [])

        if not is_plant or not results:
            print(f"   [DECISION]: NO PLANT DETECTED / UNCERTAIN (status={status})")
            if res.get("message"):
                print(f"   [MESSAGE]:  {res['message']}")
        else:
            print(f"   [DECISION]: CONFIDENT IDENTIFICATION (Count: {len(results)})")
            for rank, item in enumerate(results, 1):
                c_name = item.get("Common_Name")
                s_name = item.get("Scientific_Name")
                score = item.get("Match_Percentage")
                tier = item.get("Confidence_Tier")
                features = item.get("Verified_Features", [])
                print(f"   #{rank} {c_name} ({s_name}) | Score: {score}% | Tier: {tier}")
                feat_str = str(features[:4]).encode('ascii', errors='backslashreplace').decode('ascii')
                print(f"      Verified Features: {feat_str}")

if __name__ == "__main__":
    main()
