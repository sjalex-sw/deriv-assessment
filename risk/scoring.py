import json
from pathlib import Path


# -----------------------------
# CONFIG (from risk_model.md)
# -----------------------------

PATTERN_WEIGHTS = {
    "martingale": 25,
    "position_doubling": 20,
    "revenge_trading": 20,
    "news_chasing": 15,
    "scalping": 10,
    "anti_martingale": -10,
    "normal": 0,
    "insufficient_evidence": 0
}


RISK_TIERS = {
    (0, 25): "low",
    (25, 50): "medium",
    (50, 75): "high",
    (75, 100): "critical"
}


# -----------------------------
# NORMALIZATION HELPERS
# -----------------------------

def clamp01(x):
    return max(0.0, min(1.0, x))


def normalize(value, max_value):
    if max_value == 0:
        return 0.0
    return clamp01(value / max_value)


# -----------------------------
# FEATURE SCORE CALCULATION
# -----------------------------

def compute_feature_score(features: dict):
    score = 0

    score += normalize(features["stake_escalation_ratio_after_losses"], 3) * 20
    score += normalize(features["trades_per_minute"], 10) * 15
    score += normalize(features["news_trade_percentage"], 100) * 15
    score += normalize(features["longest_losing_streak"], 20) * 15
    score += normalize(abs(features["net_profit_loss"]), 500) * 20
    score += normalize(features["revenge_interval_seconds"], 300) * 15

    return score


# -----------------------------
# PATTERN SCORE
# -----------------------------

def compute_pattern_score(patterns: list):
    score = 0

    for p in patterns:
        score += PATTERN_WEIGHTS.get(p, 0)

    return max(0, score)


# -----------------------------
# TIER MAPPING
# -----------------------------

def assign_tier(score):
    for (low, high), tier in RISK_TIERS.items():
        if low <= score < high:
            return tier
    return "critical"


# -----------------------------
# MAIN RISK ENGINE
# -----------------------------

def compute_risk_scores(features_by_user, patterns_by_user):
    results = []

    for user_id, features in features_by_user.items():

        patterns = patterns_by_user.get(user_id, {}).get("patterns", [])

        pattern_score = compute_pattern_score(patterns)
        feature_score = compute_feature_score(features)

        total = min(100, pattern_score + feature_score)

        results.append({
            "user_id": user_id,
            "risk_score": round(total, 2),
            "risk_tier": assign_tier(total),
            "contributing_factors": {
                "pattern_score": pattern_score,
                "feature_score": feature_score
            },
            "formula_version": "risk_model_v1"
        })

    return results


# -----------------------------
# SAVE OUTPUT
# -----------------------------

def save_risk_scores(results, path="risk_scores.json"):
    Path(path).write_text(json.dumps(results, indent=2))