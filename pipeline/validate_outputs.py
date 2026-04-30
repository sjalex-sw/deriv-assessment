import json
from pathlib import Path

from pipeline.schemas import (
    UserFeatures,
    UserPatternClassification,
    RiskScore,
    Intervention,
    MartingaleAudit
)


# ---------------------------
# Generic loader
# ---------------------------

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


# ---------------------------
# FEATURE VALIDATION
# ---------------------------

def validate_features():
    feature_dir = Path("features")
    for file in feature_dir.glob("*.json"):
        data = load_json(file)
        UserFeatures(**data)  # raises if invalid


# ---------------------------
# PATTERN VALIDATION
# ---------------------------

def validate_patterns():
    data = load_json("patterns.json")
    for item in data:
        UserPatternClassification(**item)


# ---------------------------
# RISK VALIDATION
# ---------------------------

def validate_risk():
    data = load_json("risk_scores.json")
    for item in data:
        RiskScore(**item)

    # extra rule: ensure deterministic range
    for item in data:
        if not (0 <= item["risk_score"] <= 100):
            raise ValueError("Risk score out of bounds")


# ---------------------------
# INTERVENTION VALIDATION
# ---------------------------

def validate_interventions():
    data = load_json("interventions.json")
    for item in data:
        Intervention(**item)


# ---------------------------
# CROSS-STAGE CONSISTENCY CHECKS
# ---------------------------

def validate_consistency():
    patterns = load_json("patterns.json")
    risks = load_json("risk_scores.json")
    interventions = load_json("interventions.json")

    pattern_users = {p["user_id"] for p in patterns}
    risk_users = {r["user_id"] for r in risks}
    intervention_users = {i["user_id"] for i in interventions}

    if pattern_users != risk_users:
        raise ValueError("Mismatch between patterns and risk users")

    if risk_users != intervention_users:
        raise ValueError("Mismatch between risk and interventions")


# ---------------------------
# MASTER ENTRYPOINT
# ---------------------------

def run_validation():
    validate_features()
    validate_patterns()
    validate_risk()
    validate_interventions()
    validate_consistency()
    print("VALIDATION PASSED")


if __name__ == "__main__":
    run_validation()