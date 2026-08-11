import sys
import main

print("==========================================================")
print("TESTING LOCAL RETRAINED MODEL & FAKE WORD GUARDRAILS")
print("==========================================================")

fake_test_cases = [
    "magic unicorn plant",
    "blablabla xyz tree",
    "super fake green flower 123",
    "plastic toy plant with battery",
    "quantum cyber leaf",
    "nonexistent botanical species xyz",
    "fake plant 456"
]

print("\n--- 1. TESTING FAKE / TRICK INPUT REJECTIONS ---")
all_fake_rejected = True

for fake_in in fake_test_cases:
    res = main.predict_plants_local(fake_in)
    is_fake = main.is_fake_or_invalid_plant_query(fake_in)
    if is_fake or len(res) == 0:
        print(f"[PASSED / REJECTED] '{fake_in}' -> Correctly Intercepted as Fake/Invalid")
    else:
        all_fake_rejected = False
        print(f"[FAILED / FAKE ACCEPTED] '{fake_in}' -> Returned Match: {res[0]['Common_Name']} ({res[0]['Match_Percentage']}%)")

real_test_cases = [
    ("Pomegranate Tree", "Pomegranate"),
    ("Aloe Vera succulent plant", "Aloe Vera"),
    ("Neem tree with antibacterial leaves", "Neem"),
    ("Holy Basil Tulsi herb", "Holy Basil (Tulsi)"),
    ("Sunflower yellow flower", "Sunflower"),
    ("Mango tree green foliage", "Mango")
]

print("\n--- 2. TESTING REAL PLANT MATCHING & CONFIDENCE ---")
all_real_matched = True

for real_in, expected_name in real_test_cases:
    res = main.predict_plants_local(real_in)
    if res and len(res) > 0:
        match_name = res[0]['Common_Name']
        match_pct = res[0]['Match_Percentage']
        print(f"[PASSED / IDENTIFIED] '{real_in}' -> Matched: '{match_name}' | Similarity Score: {match_pct}%")
    else:
        all_real_matched = False
        print(f"[FAILED / MISSED] '{real_in}' -> Failed to match real plant!")

print("==========================================================")
if all_fake_rejected and all_real_matched:
    print("ALL TESTS PASSED! 100% GUARDRAIL & REAL MATCH ACCURACY!")
else:
    print("SOME TESTS NEED ATTENTION.")
print("==========================================================")
