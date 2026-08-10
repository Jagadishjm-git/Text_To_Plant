import urllib.request
import json
import re

# Test endpoint with description search
test_queries = [
    ("Pomegranate", "A small tree with bright red flowers, glossy leaves, and round red fruit with juicy edible seeds inside like Pomegranate"),
    ("Aloe Vera", "A medicinal plant with thick fleshy leaves and gel used for skin burns and digestive health"),
    ("Sunflower", "A tall herb with large bright yellow flower heads that track the sun and produce edible seeds")
]

for expected_name, query_text in test_queries:
    print(f"\n==========================================")
    print(f"DOM CHECK FOR: {expected_name}")
    print(f"==========================================")

    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/predict",
        data=json.dumps({"description": query_text}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            top = data["results"][0]
            print(f"DOM Card Header        : {top.get('Common_Name')} ({top.get('Scientific_Name')})")
            print(f"DOM Confidence Badge   : {top.get('Match_Percentage')}% Match")
            print(f"DOM Botanical Family   : {top.get('Family')}")
            print(f"DOM Medicinal Uses     : {top.get('Medicinal_Uses')}")
            print(f"DOM AI Explanation     : {top.get('Ai_Explanation')}")
    except Exception as e:
        print("DOM Check Error:", e)
