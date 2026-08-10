import urllib.request

url = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/66/Pomegranate_fruit.jpg/800px-Pomegranate_fruit.jpg"
headers = {'User-Agent': 'Mozilla/5.0'}

req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp, open("test_images/pomegranate.jpg", "wb") as f:
    f.write(resp.read())

print("Downloaded Wikimedia Pomegranate photo successfully!")
