import urllib.request
import json
import base64
import os
import shutil
from PIL import Image

artifact_dir = r"C:\Users\JAGADISH J M\.gemini\antigravity\brain\9b1e58e1-34da-4b63-9c7b-bdba630a6e11"

files_to_test = []
for f in os.listdir(artifact_dir):
    if f.startswith("pomegranate_plant_photo") and f.endswith(".png"):
        files_to_test.append(("Pomegranate", os.path.join(artifact_dir, f)))
    elif f.startswith("aloe_vera_plant_photo") and f.endswith(".png"):
        files_to_test.append(("Aloe Vera", os.path.join(artifact_dir, f)))
    elif f.startswith("sunflower_plant_photo") and f.endswith(".png"):
        files_to_test.append(("Sunflower", os.path.join(artifact_dir, f)))

os.makedirs("test_images", exist_ok=True)

url = "https://integrate.api.nvidia.com/v1/chat/completions"
api_key = "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"

prompt = """Examine this photo. Identify the plant, flower, fruit, or tree species.
Respond strictly in valid JSON format:
{
  "Is_Plant": true,
  "Common_Name": "Identified Plant Name (e.g. Pomegranate / Aloe Vera / Sunflower)",
  "Scientific_Name": "Binomial Scientific Name",
  "Family": "Botanical Family",
  "Plant_Type": "Tree / Herb / Shrub / Flower",
  "Habitat": "Growth Region & Habitat",
  "Medicinal_Uses": "Medicinal & Healing Uses",
  "Culinary_Uses": "Edible fruits / culinary uses",
  "Ai_Explanation": "2-3 detailed sentences explaining why this photo matches the identified species."
}
"""

test_summary_results = []

for expected_name, orig_path in files_to_test:
    target_path = f"test_images/{expected_name.lower().replace(' ', '_')}.png"
    shutil.copy(orig_path, target_path)
    
    im = Image.open(target_path)
    im.thumbnail((400, 400))
    thumb_path = f"test_images/thumb_{expected_name.lower().replace(' ', '_')}.jpg"
    im.convert("RGB").save(thumb_path, "JPEG", quality=85)

    with open(thumb_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)

    print(f"\n==========================================")
    print(f"ANALYZING: {expected_name} ({target_path})")
    print(f"==========================================")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            content = res_data['choices'][0]['message']['content'].strip()
            content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            
            print(f"[OK] Common Name   : {parsed.get('Common_Name')}")
            print(f"     Scientific Name: {parsed.get('Scientific_Name')}")
            print(f"     Family         : {parsed.get('Family')}")
            print(f"     Plant Type     : {parsed.get('Plant_Type')}")
            print(f"     AI Explanation : {parsed.get('Ai_Explanation')}")
            
            test_summary_results.append({
                "Expected": expected_name,
                "Predicted": parsed.get("Common_Name"),
                "Scientific_Name": parsed.get("Scientific_Name"),
                "Family": parsed.get("Family"),
                "Plant_Type": parsed.get("Plant_Type"),
                "Explanation": parsed.get("Ai_Explanation")
            })
    except Exception as e:
        print("ERROR:", e)

with open("test_results_summary.json", "w", encoding="utf-8") as out:
    json.dump(test_summary_results, out, indent=2)

print("\nSaved test_results_summary.json!")
