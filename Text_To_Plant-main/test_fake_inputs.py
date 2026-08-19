import urllib.request
import json

print("==========================================================")
print("TESTING FAKE WORDS AND TRICK INPUTS AGAINST LIVE API")
print("==========================================================")

endpoint = "https://text-based-plant-identification.vercel.app/api/predict"

fake_inputs = [
    "magic unicorn plant",
    "blablabla xyz tree",
    "super fake green flower 123",
    "plastic toy plant with battery",
    "quantum cyber leaf",
    "nonexistent botanical species xyz"
]

for inp in fake_inputs:
    req = urllib.request.Request(
        endpoint,
        data=json.dumps({"description": inp}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("is_plant"):
                res = data["results"][0]
                print(f"[ACCEPTED / FAKE MATCH] Input: '{inp}' -> Predicted: '{res.get('Common_Name')}' | Match: {res.get('Match_Percentage')}%")
            else:
                print(f"[REJECTED / CORRECT] Input: '{inp}' -> Message: '{data.get('error')}'")
    except Exception as e:
        print(f"[ERROR] Input: '{inp}' -> {e}")
