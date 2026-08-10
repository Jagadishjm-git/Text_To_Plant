import urllib.request

url = "https://images.unsplash.com/photo-1596489397632-159c394c8b25?auto=format&fit=crop&w=600&q=80"
headers = {'User-Agent': 'Mozilla/5.0'}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp, open("test_images/pomegranate.jpg", "wb") as f:
    f.write(resp.read())

print("Downloaded Unsplash Pomegranate tree photo successfully!")
