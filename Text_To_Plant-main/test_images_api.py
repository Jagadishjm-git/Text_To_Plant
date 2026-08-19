import urllib.request
import json
import base64

test_files = [
    ("Pomegranate", "test_images/pomegranate.jpg"),
    ("Aloe Vera", "test_images/aloe_vera.jpg"),
    ("Sunflower", "test_images/sunflower.jpg")
]

for expected_name, filepath in test_files:
    print(f"\n==========================================")
    print(f"TESTING IMAGE: {filepath} ({expected_name})")
    print(f"==========================================")
    
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    
    payload = {
        "image_b64": b64,
        "mime_type": "image/jpeg",
        "description": ""
    }
    
    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/predict",
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("is_plant") is False:
                print("FAILED: Model rejected image:", data.get("error"))
            else:
                top = data["results"][0]
                print(f"✅ Common Name   : {top.get('Common_Name')}")
                print(f"   Scientific Name: {top.get('Scientific_Name')}")
                print(f"   Family         : {top.get('Family')}")
                print(f"   Plant Type     : {top.get('Plant_Type')}")
                print(f"   Match Score    : {top.get('Match_Percentage')}%")
                print(f"   AI Explanation : {top.get('Ai_Explanation')}")
    except Exception as e:
        print("ERROR:", e)
