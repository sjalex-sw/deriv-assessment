from typing import Dict, List


# -----------------------------
# SEVERITY MAPPING
# -----------------------------

INTERVENTION_SEVERITY = {
    "soft_nudge": 1,
    "deposit_limit_prompt": 2,
    "cooling_off_period": 3,
    "human_outreach": 4
}

RISK_SEVERITY = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}


# -----------------------------
# VALIDATION RULES
# -----------------------------

def validate_intervention_alignment(intervention, patterns, risk_tier):

    issues = []

    intervention_type = intervention["intervention_type"]

    intervention_level = INTERVENTION_SEVERITY[intervention_type]
    risk_level = RISK_SEVERITY[risk_tier]

    # -----------------------------
    # 1. SEVERITY ALIGNMENT CHECK
    # -----------------------------

    # intervention should not exceed risk by 2+ levels
    if intervention_level - risk_level > 1:
        issues.append("over_escalated_intervention_for_risk_tier")

    # low risk should not get high severity intervention
    if risk_tier == "low" and intervention_type in [
        "cooling_off_period",
        "human_outreach"
    ]:
        issues.append("low_risk_over_intervention")

    # critical should not get only soft nudge
    if risk_tier == "critical" and intervention_type == "soft_nudge":
        issues.append("critical_risk_under_intervention")

    # -----------------------------
    # 2. PATTERN JUSTIFICATION
    # -----------------------------

    triggering_patterns = intervention.get("triggering_patterns", [])

    if not triggering_patterns:
        issues.append("missing_triggering_patterns")

    # ensure patterns exist in detected set
    for p in triggering_patterns:
        if p not in patterns:
            issues.append(f"invalid_trigger_pattern:{p}")

    # -----------------------------
    # 3. LOGICAL CONSISTENCY RULES
    # -----------------------------

    if intervention_type == "cooling_off_period":
        required_patterns = {"revenge_trading", "martingale", "position_doubling"}
        if not required_patterns.intersection(set(patterns)):
            issues.append("cooling_off_without_high_risk_patterns")

    if intervention_type == "deposit_limit_prompt":
        if "stake_escalation_ratio_after_losses" not in intervention.get("evidence_summary", ""):
            issues.append("deposit_limit_without_escalation_signal")

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


# -----------------------------
# BATCH VALIDATION
# -----------------------------

def validate_all_interventions(interventions, patterns_by_user, risk_by_user):

    results = []

    for item in interventions:

        user_id = item["user_id"]

        patterns = patterns_by_user.get(user_id, {}).get("patterns", [])
        risk_tier = risk_by_user[user_id]["risk_tier"]

        result = validate_intervention_alignment(
            item,
            patterns,
            risk_tier
        )

        results.append({
            "user_id": user_id,
            **result
        })

    return results