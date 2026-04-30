from typing import Dict, List


# -----------------------------
# THRESHOLDS (tunable but explicit)
# -----------------------------

THRESHOLDS = {
    "stake_escalation": 1.8,
    "long_losing_streak": 5,
    "revenge_interval": 120,  # seconds
    "news_exposure": 30  # percent
}


# -----------------------------
# RULE CHECKS PER PATTERN
# -----------------------------

def check_martingale(features):
    return features["stake_escalation_ratio_after_losses"] >= THRESHOLDS["stake_escalation"]


def check_revenge(features):
    return features["revenge_interval_seconds"] <= THRESHOLDS["revenge_interval"]


def check_news_chasing(features):
    return features["news_trade_percentage"] >= THRESHOLDS["news_exposure"]


def check_losing_streak(features):
    return features["longest_losing_streak"] >= THRESHOLDS["long_losing_streak"]


# -----------------------------
# VALIDATION CORE
# -----------------------------

def validate_user_consistency(user_id, features, patterns, risk):
    issues = []

    pattern_set = set(patterns)

    # -------------------------
    # 1. MARTINGALE CONSISTENCY
    # -------------------------
    if "martingale" in pattern_set:
        if not check_martingale(features):
            issues.append("martingale_flag_but_no_stake_escalation")

    # -------------------------
    # 2. REVENGE TRADING
    # -------------------------
    if "revenge_trading" in pattern_set:
        if not check_revenge(features):
            issues.append("revenge_trading_flag_but_no_short_revenge_interval")

    # -------------------------
    # 3. NEWS CHASING
    # -------------------------
    if "news_chasing" in pattern_set:
        if not check_news_chasing(features):
            issues.append("news_chasing_flag_but_low_news_exposure")

    # -------------------------
    # 4. HIGH RISK WITHOUT SIGNALS
    # -------------------------
    if risk["risk_tier"] in ["high", "critical"]:
        if len(pattern_set) == 0 or pattern_set == {"normal"}:
            issues.append("high_risk_without_strong_patterns")

    # -------------------------
    # 5. FEATURE SIGNAL WITHOUT PATTERN
    # -------------------------
    if check_martingale(features) and "martingale" not in pattern_set:
        issues.append("stake_escalation_present_but_no_martingale_detected")

    if check_revenge(features) and "revenge_trading" not in pattern_set:
        issues.append("revenge_behavior_present_but_not_classified")

    return {
        "user_id": user_id,
        "valid": len(issues) == 0,
        "issues": issues
    }


# -----------------------------
# BATCH VALIDATION
# -----------------------------

def run_integrity_checks(features_by_user, patterns_by_user, risk_by_user):
    results = []

    for user_id in features_by_user:

        features = features_by_user[user_id]
        patterns = patterns_by_user.get(user_id, {}).get("patterns", [])
        risk = risk_by_user.get(user_id)

        result = validate_user_consistency(
            user_id,
            features,
            patterns,
            risk
        )

        results.append(result)

    return results