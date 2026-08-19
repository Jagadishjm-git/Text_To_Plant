import urllib.request
import json
import base64
import time
import os

print("==========================================================")
print("LIVE VERCEL ENDPOINT CROSS-CHECK VERIFICATION")
print("URL: https://text-based-plant-identification.vercel.app/api/predict")
print("==========================================================")

endpoint = "https://text-based-plant-identification.vercel.app/api/predict"

# Load image if available
image_b64 = None
if os.path.exists("test_images/thumb_aloe_vera.jpg"):
    with open("test_images/thumb_aloe_vera.jpg", "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

test_cases = [
    ("1. Pomegranate Query", {"description": "A small tree with bright red flowers, glossy leaves, and round red fruit with juicy edible seeds inside like Pomegranate."}, "pomegranate"),
    ("2. Aloe Vera Query", {"description": "A medicinal plant with thick fleshy leaves and gel used for skin burns and digestive health."}, "aloe"),
    ("3. Sunflower Query", {"description": "A tall herb with large bright yellow flower heads that track the sun."}, "sunflower"),
    ("4. Neem Tree Query", {"description": "Neem tree with pinnate leaves, white flowers, antibacterial properties."}, "neem"),
    ("5. Non-Plant (Laptop Charger)", {"description": "blue laptop charger with 65W power adapter"}, None),
    ("6. Non-Plant (Sports Car)", {"description": "red sports car with twin turbo V8 engine"}, None),
    ("7. Non-Plant (Gibberish)", {"description": "asdfghjkl 123456 test string"}, None),
]

if image_b64:
    test_cases.append(("8. Image Upload (Aloe Vera Photo)", {"description": "Identify plant photo", "image_b64": image_b64, "mime_type": "image/jpeg"}, "aloe"))

passed_count = 0
total_cases = len(test_cases)

for name, payload, expected_keyword in test_cases:
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = round((time.time() - start_t) * 1000)
            data = json.loads(resp.read().decode('utf-8'))
            
            if expected_keyword is None:
                # Expect rejection
                if not data.get("is_plant"):
                    passed_count += 1
                    err_msg = data.get("error", "No plant detected")
                    print(f"[PASS] {name} -> Correctly Rejected ({err_msg}) | {elapsed}ms")
                else:
                    pred = data.get("results", [{}])[0].get("Common_Name", "Unknown")
                    print(f"[FAIL] {name} -> Mistakenly Accepted as '{pred}' | {elapsed}ms")
            else:
                # Expect positive identification
                if data.get("is_plant") and data.get("results"):
                    first = data["results"][0]
                    c_name = first.get("Common_Name", "")
                    s_name = first.get("Scientific_Name", "")
                    match_pct = first.get("Match_Percentage", 0)
                    passed_count += 1
                    print(f"[PASS] {name} -> Predicted: '{c_name}' ({s_name}) | Match: {match_pct}% | {elapsed}ms")
                else:
                    err = data.get("error", "No prediction returned")
                    print(f"[FAIL] {name} -> Failed ({err}) | {elapsed}ms")

    except Exception as e:
        print(f"[ERROR] {name} -> Network / Exception: {e}")

print("==========================================================")
print(f"VERIFICATION SUMMARY: {passed_count} / {total_cases} PASSED ({round(passed_count/total_cases*100, 1)}%)")
print("==========================================================")
