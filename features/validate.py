import json
import math
from pathlib import Path

from pipeline.schemas import UserFeatures


# -----------------------------
# LOAD FEATURE FILE
# -----------------------------

def load_feature_file(path: str):
    with open(path, "r") as f:
        return json.load(f)


# -----------------------------
# BASIC NUMERIC SAFETY
# -----------------------------

def is_finite_number(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


# -----------------------------
# SINGLE USER VALIDATION
# -----------------------------

def validate_user_features(feature: dict):
    # 1. Schema validation (hard gate)
    validated = UserFeatures(**feature)

    # 2. Numeric sanity checks
    checks = {
        "average_stake": validated.average_stake >= 0,
        "trades_per_minute": validated.trades_per_minute >= 0,
        "longest_losing_streak": validated.longest_losing_streak >= 0,
        "total_trades": validated.total_trades >= 0,
        "revenge_interval_seconds": validated.revenge_interval_seconds >= 0,
    }

    for field, ok in checks.items():
        if not ok:
            raise ValueError(f"Invalid value for {field}")

    # 3. Probability bounds
    if not (0 <= validated.win_rate <= 1):
        raise ValueError("win_rate out of bounds [0,1]")

    if not (0 <= validated.news_trade_percentage <= 100):
        raise ValueError("news_trade_percentage out of bounds [0,100]")

    # 4. Net PnL sanity
    if not is_finite_number(validated.net_profit_loss):
        raise ValueError("net_profit_loss is not finite")

    # 5. Cross-field consistency checks
    stats = validated.supporting_stats

    if stats["trade_count"] != validated.total_trades:
        raise ValueError("trade_count mismatch with total_trades")

    if stats["win_count"] + stats["loss_count"] != validated.total_trades:
        raise ValueError("win/loss count mismatch")

    if stats["escalation_samples"] > validated.total_trades:
        raise ValueError("invalid escalation sample count")

    return True


# -----------------------------
# PIPELINE-WIDE VALIDATION
# -----------------------------

def validate_all_features(feature_dir: str = "features"):
    path = Path(feature_dir)

    if not path.exists():
        raise FileNotFoundError("features directory not found")

    files = list(path.glob("*.json"))

    if not files:
        raise ValueError("no feature files found")

    results = {}

    for file in files:
        data = load_feature_file(file)

        try:
            validate_user_features(data)
            results[data["user_id"]] = "valid"
        except Exception as e:
            raise ValueError(f"Validation failed for {file.name}: {str(e)}")

    return results

import json
from pathlib import Path

PATTERN_VOCAB = {
    "martingale",
    "anti_martingale",
    "revenge_trading",
    "news_chasing",
    "scalping",
    "position_doubling",
    "normal",
    "insufficient_evidence"
}

CONFIDENCE_VOCAB = {"low", "medium", "high"}

def validate_pattern_record(record, allowed_trade_ids: set):
    # user_id
    if "user_id" not in record:
        raise ValueError("Missing user_id")

    # patterns
    patterns = record.get("patterns", [])
    if not isinstance(patterns, list) or len(patterns) == 0:
        raise ValueError("patterns must be non-empty list")

    for p in patterns:
        if p not in PATTERN_VOCAB:
            raise ValueError(f"Invalid pattern: {p}")

    # confidence
    confidence = record.get("confidence")
    if confidence not in CONFIDENCE_VOCAB:
        raise ValueError(f"Invalid confidence: {confidence}")

    # evidence
    evidence = record.get("evidence")
    if not isinstance(evidence, list):
        raise ValueError("evidence must be a list")

    for e in evidence:
        if not isinstance(e, dict):
            raise ValueError("evidence items must be objects")

        required_keys = {"pattern", "triggering_features", "trade_ids", "explanation"}
        if not required_keys.issubset(e.keys()):
            raise ValueError("missing keys in evidence object")

        if e["pattern"] not in PATTERN_VOCAB:
            raise ValueError(f"Invalid evidence pattern: {e['pattern']}")

        if not isinstance(e["trade_ids"], list):
            raise ValueError("trade_ids must be list")

        # ensure trade_ids exist in dataset
        for tid in e["trade_ids"]:
            if tid not in allowed_trade_ids:
                raise ValueError(f"Unknown trade_id referenced: {tid}")

def validate_patterns_file(patterns_path="patterns.json", trades=None):
    if trades is None:
        raise ValueError("trades set required for validation")

    allowed_trade_ids = {t["trade_id"] for t in trades}

    with open(patterns_path, "r") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("patterns.json must be a list")

    seen_users = set()

    for record in data:
        validate_pattern_record(record, allowed_trade_ids)

        uid = record["user_id"]
        if uid in seen_users:
            raise ValueError(f"Duplicate user_id in patterns: {uid}")
        seen_users.add(uid)

    return True


