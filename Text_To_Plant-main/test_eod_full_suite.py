"""
test_eod_full_suite.py
End-of-Day (EOD) Complete Automated Verification Suite
Tests:
1. Morphological Trait Descriptions (without naming plants)
2. Exact Plant Name Searches (Single-result isolation)
3. Generic & Ambiguous Descriptions (UNCERTAIN guardrail)
4. Non-Plant & Hardware Queries (REJECTED guardrail)
5. Department Authentication, Subscription Access & Admin Isolation
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from botanical_pipeline import execute_plant_identification_pipeline, get_db_engine
from main import is_fake_or_invalid_plant_query
from test_auth_and_access import run_all_tests as run_auth_tests

def run_eod_verification():
    print("=" * 90)
    print("🌿 COMPLETE END-OF-DAY (EOD) BOTANICAL PORTAL VERIFICATION SUITE")
    print("=" * 90)

    engine = get_db_engine()
    print(f"✓ Dataset Loaded: {len(engine.plants)} records indexed in engine.")
    print("-" * 90)

    # -------------------------------------------------------------
    # SECTION 1: TRAIT DESCRIPTIONS (Identifying without plant names)
    # -------------------------------------------------------------
    print("\n[SECTION 1: NATURAL TRAIT DESCRIPTIONS - NO NAMES]")
    trait_tests = [
        ("A large tree with alternate lanceolate leaves, pale yellow panicle flowers, and sweet yellow-orange drupe fruit.", "Mango"),
        ("A small tree with glossy leaves, red flowers, and round red fruits with juicy edible seeds inside.", "Pomegranate"),
        ("Succulent herb with thick fleshy serrated leaves arranged in a rosette and medicinal gel used for skin burns.", "Aloe Vera"),
        ("A large tree with alternate compound pinnate lanceolate leaves, white panicle flowers, and yellow drupes with strong antibacterial properties.", "Neem"),
        ("An aquatic herb found in ponds and lakes with large floating orbicular leaves, pink and white solitary flowers, and rhizome roots.", "Lotus"),
        ("An aromatic herb with opposite ovate leaves, purple-white spike flowers, and medicinal properties for respiratory health and herbal tea.", "Holy Basil (Tulsi)"),
        ("A large tropical tree with alternate cordate leaves featuring a distinct drip tip and purple syconium fig fruits.", "Peepal (Sacred Fig)"),
        ("A perennial herb with oblong-lanceolate leaves, pseudostem, pale yellow spike flowers, and yellow-orange medicinal rhizome roots.", "Turmeric"),
        ("A tall palm tree with linear compound pinnate leaves, pale yellow spadix flowers, fibrous roots, and large green-brown drupes in coastal regions.", "Coconut")
    ]

    all_passed = True

    for q, expected in trait_tests:
        res = execute_plant_identification_pipeline(q)
        results = res.get("results", [])
        if results:
            top = results[0]
            name = top.get("Common_Name")
            pct = top.get("Match_Percentage")
            tier = top.get("Confidence_Tier")
            feats = top.get("Matching_Features", [])

            # Check if expected is in name
            match_ok = expected.lower() in name.lower() or name.lower() in expected.lower()
            status = "PASS ✓" if match_ok and pct >= 90 else "FAIL ✗"
            if not (match_ok and pct >= 90):
                all_passed = False

            print(f"  Target: {expected:<22} | Found: {name:<22} | Score: {pct}% {tier:<8} | Count: {len(results)} | {status}")
            print(f"     Verified Traits: {feats[:4]}")
        else:
            print(f"  Target: {expected:<22} | FAILED (Uncertain): {res.get('message')}")
            all_passed = False

    # -------------------------------------------------------------
    # SECTION 2: EXACT NAME SEARCHES (Single Result Isolation)
    # -------------------------------------------------------------
    print("\n[SECTION 2: EXACT PLANT NAME SEARCHES - 1 RESULT ISOLATION]")
    exact_tests = [
        ("Pomegranate Tree", "Pomegranate"),
        ("Aloe Vera", "Aloe Vera"),
        ("Neem Tree", "Neem"),
        ("Turmeric", "Turmeric"),
        ("Mango", "Mango")
    ]

    for q, expected in exact_tests:
        res = execute_plant_identification_pipeline(q)
        results = res.get("results", [])
        count = len(results)
        top = results[0] if count > 0 else {}
        name = top.get("Common_Name", "")
        pct = top.get("Match_Percentage", 0)
        tier = top.get("Confidence_Tier", "")

        is_single = (count == 1)
        name_ok = expected.lower() in name.lower()
        score_ok = (pct >= 90)

        status = "PASS ✓" if (is_single and name_ok and score_ok) else "FAIL ✗"
        if not (is_single and name_ok and score_ok):
            all_passed = False

        print(f"  Query: '{q:<18}' | Found: {name:<18} | Count: {count} (Exact 1) | Score: {pct}% {tier} | {status}")

    # -------------------------------------------------------------
    # SECTION 3: GENERIC & AMBIGUOUS DESCRIPTIONS (UNCERTAIN)
    # -------------------------------------------------------------
    print("\n[SECTION 3: GENERIC & AMBIGUOUS INPUTS - UNCERTAIN GUARDRAIL]")
    generic_tests = [
        "green leaves medicinal tree",
        "tropical plant with green leaves"
    ]

    for q in generic_tests:
        res = execute_plant_identification_pipeline(q)
        is_unc = (res.get("status") == "UNCERTAIN" or not res.get("is_plant"))
        status = "PASS ✓" if is_unc else "FAIL ✗"
        if not is_unc:
            all_passed = False
        print(f"  Query: '{q:<35}' | Status: {res.get('status')} | Confidence: {res.get('confidence', 0)}% | {status}")

    # -------------------------------------------------------------
    # SECTION 4: NON-PLANT & GIBBERISH INPUTS (REJECTED)
    # -------------------------------------------------------------
    print("\n[SECTION 4: NON-PLANT & GIBBERISH INPUTS - REJECTED GUARDRAIL]")
    non_plant_tests = [
        "Laptop charger 65W",
        "intel core i9 processor 32GB ram",
        "asdfghjkl 123"
    ]

    for q in non_plant_tests:
        is_fake = is_fake_or_invalid_plant_query(q)
        if is_fake:
            print(f"  Query: '{q:<35}' | Filter: REJECTED (Non-Plant) | PASS ✓")
        else:
            res = execute_plant_identification_pipeline(q)
            is_rej = (not res.get("is_plant"))
            status = "PASS ✓" if is_rej else "FAIL ✗"
            if not is_rej:
                all_passed = False
            print(f"  Query: '{q:<35}' | Status: {res.get('status')} | {status}")

    # -------------------------------------------------------------
    # SECTION 5: AUTHENTICATION & SUBSCRIPTION TEST SUITE
    # -------------------------------------------------------------
    print("\n[SECTION 5: DEPARTMENT AUTHENTICATION & ACCESS CONTROL]")
    auth_ok = run_auth_tests()
    if not auth_ok:
        all_passed = False

    print("\n" + "=" * 90)
    print("EOD FULL VERIFICATION SUMMARY: " + ("100% ALL SYSTEMS VERIFIED & PASSING!" if all_passed else "SOME FAILURES OCCURRED"))
    print("=" * 90)
    return all_passed

if __name__ == "__main__":
    success = run_eod_verification()
    sys.exit(0 if success else 1)
