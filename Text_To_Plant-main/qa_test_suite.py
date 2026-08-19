import urllib.request
import json
import base64
import os

print("==========================================")
print("RUNNING QA TEST SUITE FOR BOTANICAL PORTAL")
print("==========================================")

base_urls = [
    ("Local Server", "http://127.0.0.1:5000/api/predict"),
    ("Vercel Live Server", "https://text-based-plant-identification.vercel.app/api/predict")
]

with open("test_images/thumb_aloe_vera.jpg", "rb") as f:
    aloe_b64 = base64.b64encode(f.read()).decode('utf-8')

test_cases = [
    ("TC-1: Text Query (Pomegranate)", {"description": "A small tree with bright red flowers, glossy leaves, and round red fruit with juicy edible seeds inside like Pomegranate."}),
    ("TC-2: Text Query (Aloe Vera)", {"description": "A medicinal plant with thick fleshy leaves and gel used for skin burns and digestive health."}),
    ("TC-3: Text Query (Sunflower)", {"description": "A tall herb with large bright yellow flower heads that track the sun."}),
    ("TC-4: Non-Plant Text (Laptop Charger)", {"description": "blue laptop charger with 65W power adapter"}),
    ("TC-5: Image Upload (Aloe Vera Photo)", {"description": "Identify plant photo", "image_b64": aloe_b64, "mime_type": "image/jpeg"})
]

for server_name, endpoint in base_urls:
    print(f"\n------------------------------------------")
    print(f"TESTING ENDPOINT: {server_name} ({endpoint})")
    print(f"------------------------------------------")

    for tc_name, payload in test_cases:
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
                if data.get("is_plant") is False:
                    print(f"[REJECTED] {tc_name} -> Non-Plant Output: \"{data.get('error')}\"")
                else:
                    first = data["results"][0]
                    print(f"[PASSED]   {tc_name} -> Predicted: {first.get('Common_Name')} ({first.get('Scientific_Name')}) | Match: {first.get('Match_Percentage')}%")
        except Exception as e:
            print(f"[ERROR]    {tc_name} -> Network Error: {e}")

print("\n==========================================")
print("QA TEST SUITE COMPLETED")
print("==========================================")
