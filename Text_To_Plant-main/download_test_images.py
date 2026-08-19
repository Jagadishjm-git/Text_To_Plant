import urllib.request
import os

os.makedirs("test_images", exist_ok=True)

images = {
    "test_images/pomegranate.jpg": "https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=600&q=80",
    "test_images/aloe_vera.jpg": "https://images.unsplash.com/photo-1596547609652-9cf5d8d76921?auto=format&fit=crop&w=600&q=80",
    "test_images/sunflower.jpg": "https://images.unsplash.com/photo-1597848212624-a19eb35e2651?auto=format&fit=crop&w=600&q=80"
}

headers = {'User-Agent': 'Mozilla/5.0'}

for path, url in images.items():
    print(f"Downloading {path}...")
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(path, 'wb') as f:
        f.write(resp.read())

print("Downloaded 3 plant test images successfully!")
