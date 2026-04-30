import json
import os
from pathlib import Path


REQUIRED_FILES = [
    "trades.json",
    "economic_calendar.json",
    "patterns.json",
    "risk_scores.json",
    "interventions.json",
    "llm_calls.jsonl"
]


# -----------------------------
# 1. FILE EXISTENCE CHECK
# -----------------------------

def check_required_files():
    missing = []

    for f in REQUIRED_FILES:
        if not Path(f).exists():
            missing.append(f)

    if missing:
        raise ValueError(f"Missing required files: {missing}")

    print("✔ Required artifacts exist")


# -----------------------------
# 2. JSON VALIDITY CHECK
# -----------------------------

def check_json_validity():

    json_files = [
        "trades.json",
        "economic_calendar.json",
        "patterns.json",
        "risk_scores.json",
        "interventions.json"
    ]

    for f in json_files:
        try:
            with open(f, "r") as fp:
                json.load(fp)
        except Exception as e:
            raise ValueError(f"Invalid JSON in {f}: {e}")

    print("✔ JSON files valid")


# -----------------------------
# 3. FEATURE FILES PER USER
# -----------------------------

def check_feature_files():
    feature_dir = Path("features")

    if not feature_dir.exists():
        raise ValueError("Missing features/ directory")

    feature_files = list(feature_dir.glob("*.json"))

    if not feature_files:
        raise ValueError("No feature files found")

    print("✔ Feature files exist")


# -----------------------------
# 4. RISK MUST BE DETERMINSITIC
# -----------------------------

def check_risk_determinism():
    """
    Simple heuristic:
    - risk_scores must not contain LLM markers or randomness flags
    """

    with open("risk_scores.json") as f:
        data = json.load(f)

    for r in data:
        if "llm" in json.dumps(r).lower():
            raise ValueError("Risk score contains LLM-generated data (invalid)")

    print("✔ Risk scoring appears deterministic")


# -----------------------------
# 5. INTERVENTION VALIDATION
# -----------------------------

def check_interventions():
    with open("interventions.json") as f:
        data = json.load(f)

    with open("patterns.json") as f:
        patterns = {p["user_id"]: p for p in json.load(f)}

    with open("risk_scores.json") as f:
        risks = {r["user_id"]: r for r in json.load(f)}

    for i in data:

        uid = i["user_id"]

        if uid not in risks:
            raise ValueError(f"Invalid user in interventions: {uid}")

        if uid not in patterns:
            raise ValueError(f"Missing pattern for user: {uid}")

        if not i.get("triggering_patterns"):
            raise ValueError(f"No triggering patterns for {uid}")

    print("✔ Interventions valid")


# -----------------------------
# 6. LLM CALL AUDIT CHECK
# -----------------------------

def check_llm_logs():
    with open("llm_calls.jsonl") as f:
        lines = f.readlines()

    pattern_calls = [
        json.loads(l) for l in lines
        if "PATTERN_DETECTION" in l
    ]

    users = set()
    for call in pattern_calls:
        uid = call.get("user_id")
        if uid:
            users.add(uid)

    # crude check: must match pattern users
    with open("patterns.json") as f:
        patterns = json.load(f)

    pattern_users = {p["user_id"] for p in patterns}

    if users != pattern_users:
        raise ValueError(
            "Mismatch between LLM calls and pattern outputs"
        )

    print("✔ LLM call logs consistent")


# -----------------------------
# 7. PIPELINE ORDER CHECK
# -----------------------------

def check_pipeline_order():
    """
    Ensures:
    features → patterns → risk → interventions
    """

    # crude timestamp / file dependency check
    if Path("risk_scores.json").stat().st_mtime < Path("patterns.json").stat().st_mtime:
        raise ValueError("Risk computed before patterns")

    if Path("interventions.json").stat().st_mtime < Path("risk_scores.json").stat().st_mtime:
        raise ValueError("Interventions computed before risk")

    print("✔ Pipeline order valid")


# -----------------------------
# 8. U_001 HARD CHECK (SPECIAL CASE)
# -----------------------------

def check_u001():
    if not Path("patterns.json").exists():
        return

    with open("patterns.json") as f:
        data = json.load(f)

    u001 = next((p for p in data if p["user_id"] == "u_001"), None)

    if not u001:
        print("⚠ u_001 not present")
        return

    if not any(p in u001["patterns"] for p in ["martingale", "position_doubling"]):
        raise ValueError("u_001 missing required martingale/position_doubling detection")

    print("✔ u_001 validation passed")


# -----------------------------
# MAIN ENTRYPOINT
# -----------------------------

def main():
    print("\n=== VALIDATION START ===")

    check_required_files()
    check_json_validity()
    check_feature_files()
    check_risk_determinism()
    check_interventions()
    check_llm_logs()
    check_pipeline_order()
    check_u001()

    print("\n✔ ALL VALIDATIONS PASSED")


if __name__ == "__main__":
    main()