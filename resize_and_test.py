import urllib.request
import json
import base64
import os
from PIL import Image

url = "https://integrate.api.nvidia.com/v1/chat/completions"
api_key = "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"

test_files = [
    ("Pomegranate", "test_images/pomegranate.jpg"),
    ("Aloe Vera", "test_images/aloe_vera.jpg"),
    ("Sunflower", "test_images/sunflower.jpg")
]

for name, path in test_files:
    print(f"\nResizing & Testing {name} ({path})...")
    # Resize image to max 400px
    im = Image.open(path)
    im.thumbnail((400, 400))
    resized_path = f"test_images/thumb_{os.path.basename(path)}"
    im.save(resized_path, "JPEG", quality=85)

    with open(resized_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')

    prompt = """Analyze this photo. Identify the plant, flower, fruit, or tree species.
Respond strictly in valid JSON format:
{
  "Is_Plant": true,
  "Common_Name": "Identified Species Name (e.g., Sunflower / Aloe Vera / Pomegranate)",
  "Scientific_Name": "Binomial Scientific Name",
  "Family": "Botanical Family",
  "Plant_Type": "Tree / Shrub / Herb / Flower",
  "Ai_Explanation": "1-2 sentences explaining why this photo matches the plant species."
}
If no plant or flower is in the photo:
{
  "Is_Plant": false,
  "Message": "No plant detected."
}
"""

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
        "max_tokens": 300
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print("SUCCESS:")
            print(data['choices'][0]['message']['content'])
    except Exception as e:
        print("ERROR:", e)
