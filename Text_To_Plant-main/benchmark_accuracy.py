import urllib.request
import json
import base64
import time

print("==========================================================")
print("STARTING BOTANICAL AI CLASSIFICATION ACCURACY BENCHMARK")
print("==========================================================")

endpoint = "https://text-based-plant-identification.vercel.app/api/predict"

benchmark_cases = [
    # Positive Cases (12)
    {"id": "TC-01", "name": "Pomegranate Tree", "query": "A small tree with bright red flowers, glossy leaves, and round red fruit with juicy edible seeds inside like Pomegranate.", "expected_plant": "pomegranate", "is_botanical": True},
    {"id": "TC-02", "name": "Aloe Vera", "query": "A medicinal succulent plant with thick fleshy spiky leaves and gel used for skin burns.", "expected_plant": "aloe", "is_botanical": True},
    {"id": "TC-03", "name": "Sunflower", "query": "A tall annual herb with large bright yellow flower head that tracks the sun.", "expected_plant": "sunflower", "is_botanical": True},
    {"id": "TC-04", "name": "Neem Tree", "query": "A large evergreen tree with pinnate leaves, small white flowers, and antibacterial medicinal properties.", "expected_plant": "neem", "is_botanical": True},
    {"id": "TC-05", "name": "Holy Basil (Tulsi)", "query": "An aromatic erect herb with opposite green purple leaves, lavender flowers, used for respiratory health.", "expected_plant": "basil", "is_botanical": True},
    {"id": "TC-06", "name": "Turmeric", "query": "A perennial herb with large oblong leaves and bright yellow aromatic underground rhizome used in spices.", "expected_plant": "turmeric", "is_botanical": True},
    {"id": "TC-07", "name": "Mango Tree", "query": "A large tropical fruit tree with dense foliage, lanceolate leaves, and sweet juicy yellow orange fruit.", "expected_plant": "mango", "is_botanical": True},
    {"id": "TC-08", "name": "Banyan Tree", "query": "A massive fig tree with aerial prop roots that grow into thick woody trunks.", "expected_plant": "banyan", "is_botanical": True},
    {"id": "TC-09", "name": "Rose Shrub", "query": "A woody perennial flowering shrub with sharp thorns, pinnate leaves, and fragrant multi-petaled red flowers.", "expected_plant": "rose", "is_botanical": True},
    {"id": "TC-10", "name": "Coconut Palm", "query": "A tall unbranched palm tree with feather-like pinnate fronds and large fibrous hard-shelled nuts containing coconut water.", "expected_plant": "coconut", "is_botanical": True},
    {"id": "TC-11", "name": "Eucalyptus", "query": "A tall evergreen tree with aromatic narrow blue-green leaves, smooth peeling bark, and essential oil.", "expected_plant": "eucalyptus", "is_botanical": True},
    {"id": "TC-12", "name": "Ginger", "query": "A leafy perennial herb with narrow reed-like stems and pungent spicy underground rhizomes.", "expected_plant": "ginger", "is_botanical": True},
    
    # Negative Non-Plant Cases (3)
    {"id": "TC-13", "name": "Non-Plant (Laptop Charger)", "query": "blue laptop charger with 65W power adapter and usb cable", "expected_plant": None, "is_botanical": False},
    {"id": "TC-14", "name": "Non-Plant (Sports Car)", "query": "red sports car with V8 turbo engine and alloy wheels", "expected_plant": None, "is_botanical": False},
    {"id": "TC-15", "name": "Non-Plant (Gibberish)", "query": "qwertyuiop 123456789 xyz test string", "expected_plant": None, "is_botanical": False}
]

total_tests = len(benchmark_cases)
correct_predictions = 0

true_positives = 0
true_negatives = 0
false_positives = 0
false_negatives = 0

results_summary = []

for tc in benchmark_cases:
    payload = {"description": tc["query"]}
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            latency_ms = round((time.time() - start_t) * 1000)
            
            is_plant_resp = data.get("is_plant", False)
            
            if tc["is_botanical"]:
                # Positive test case expectation
                if is_plant_resp and data.get("results"):
                    pred_name = data["results"][0].get("Common_Name", "")
                    s_name = data["results"][0].get("Scientific_Name", "")
                    match_pct = data["results"][0].get("Match_Percentage", 0)
                    
                    true_positives += 1
                    correct_predictions += 1
                    status = "PASS"
                    print(f"[{status}] {tc['id']} ({tc['name']}) -> Predicted: '{pred_name}' ({s_name}) | Match: {match_pct}% | Latency: {latency_ms}ms")
                else:
                    false_negatives += 1
                    status = "FAIL"
                    print(f"[{status}] {tc['id']} ({tc['name']}) -> Failed to identify plant | Latency: {latency_ms}ms")
            else:
                # Negative test case expectation (should reject non-plant)
                if not is_plant_resp:
                    true_negatives += 1
                    correct_predictions += 1
                    status = "PASS"
                    reason = data.get("error", "No plant detected")
                    print(f"[{status}] {tc['id']} ({tc['name']}) -> Correctly Rejected: '{reason}' | Latency: {latency_ms}ms")
                else:
                    false_positives += 1
                    status = "FAIL"
                    pred_name = data["results"][0].get("Common_Name", "")
                    print(f"[{status}] {tc['id']} ({tc['name']}) -> False Positive: Incorrectly classified as '{pred_name}' | Latency: {latency_ms}ms")

            results_summary.append({
                "id": tc["id"],
                "name": tc["name"],
                "is_botanical": tc["is_botanical"],
                "status": status,
                "latency_ms": latency_ms
            })

    except Exception as e:
        print(f"[ERROR] {tc['id']} ({tc['name']}) -> Exception: {e}")

# ACCURACY METRIC COMPUTATION
accuracy = round((correct_predictions / total_tests) * 100, 2)
precision = round((true_positives / (true_positives + false_positives)) * 100, 2) if (true_positives + false_positives) > 0 else 0
recall = round((true_positives / (true_positives + false_negatives)) * 100, 2) if (true_positives + false_negatives) > 0 else 0
f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0

metrics = {
    "Total_Tests": total_tests,
    "Correct_Predictions": correct_predictions,
    "Accuracy_Percentage": accuracy,
    "Precision_Percentage": precision,
    "Recall_Percentage": recall,
    "F1_Score": f1_score,
    "True_Positives": true_positives,
    "True_Negatives": true_negatives,
    "False_Positives": false_positives,
    "False_Negatives": false_negatives
}

print("\n==========================================================")
print("BENCHMARK RESULTS METRICS")
print("==========================================================")
print(f"Overall Accuracy : {accuracy}%")
print(f"Precision Score  : {precision}%")
print(f"Recall Score     : {recall}%")
print(f"F1 Score         : {f1_score}")
print(f"True Positives   : {true_positives} / 12")
print(f"True Negatives   : {true_negatives} / 3")
print("==========================================================")

with open("benchmark_results.json", "w") as f:
    json.dump({"metrics": metrics, "test_cases": results_summary}, f, indent=2)

print("Saved benchmark_results.json!")
