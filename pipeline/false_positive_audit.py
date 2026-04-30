import json
from pathlib import Path


# -----------------------------
# MARTINGALE DETECTOR (DETERMINISTIC)
# -----------------------------

def detect_martingale_sequence(trades):
    """
    Returns:
        - sequence of trade_ids if escalation after loss is found
        - explanation string
    """

    if not trades:
        return None, "no_trades"

    sequence = []
    last_loss_stake = None

    for t in trades:

        if t["result"] == "loss":
            last_loss_stake = t["stake_usd"]
            sequence.append(t["trade_id"])

        elif t["result"] == "win" and last_loss_stake is not None:
            # check if stake increased after loss sequence
            if t["stake_usd"] > last_loss_stake:
                sequence.append(t["trade_id"])
                return sequence, "stake_escalation_after_loss_detected"

    return None, "no_martingale_pattern_found"

def run_false_positive_audit(trades_by_user, patterns_by_user):

    results = []

    martingale_users = [
        uid for uid, p in patterns_by_user.items()
        if "martingale" in p.get("patterns", [])
    ]

    if not martingale_users:
        return [{
            "user_id": None,
            "pattern": "martingale",
            "verified": False,
            "supporting_trade_sequence": [],
            "calculation": "no_users_classified_as_martingale"
        }]

    for user_id in martingale_users:

        trades = trades_by_user[user_id]

        sequence, explanation = detect_martingale_sequence(trades)

        results.append({
            "user_id": user_id,
            "pattern": "martingale",
            "verified": sequence is not None,
            "supporting_trade_sequence": sequence or [],
            "calculation": explanation
        })

    return results