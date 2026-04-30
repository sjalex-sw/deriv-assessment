import json
from pathlib import Path

from features.engine import FeatureEngine, Trade, parse_ts, write_features
from features.validate import validate_all_features, validate_patterns_file
from risk.scoring import compute_risk_scores, save_risk_scores
from pipeline.integrity import run_integrity_checks

from pipeline.validate_interventions import validate_all_interventions

from llm.intervention_planning import run_intervention_planning, save_interventions
from llm.contract import ContractRunner
from llm.openai_client import OpenAILLMClient

from llm.contract import ContractRunner
from llm.openai_client import OpenAILLMClient
from llm.pattern_detection import run_pattern_detection


# -----------------------------
# CONFIG
# -----------------------------

TRADES_PATH = "trades.json"
NEWS_PATH = "economic_calendar.json"

FEATURES_DIR = "features"
PATTERNS_PATH = "patterns.json"


# -----------------------------
# LOADERS
# -----------------------------

def load_trades(path: str):
    with open(path, "r") as f:
        data = json.load(f)

    trades = []

    for t in data["trades"]:
        trades.append(
            Trade(
                user_id=t["user_id"],
                trade_id=t["trade_id"],
                open_ts=parse_ts(t["open_ts"]),
                close_ts=parse_ts(t["close_ts"]),
                stake_usd=float(t["stake_usd"]),
                payout_usd=float(t["payout_usd"]),
                result=t["result"],
                session_id=t["session_id"],
            )
        )

    return trades


def load_news(path: str):
    with open(path, "r") as f:
        return json.load(f)


# -----------------------------
# GROUP DATA BY USER (needed for stage 2)
# -----------------------------

def group_trades_by_user(trades):
    grouped = {}

    for t in trades:
        grouped.setdefault(t.user_id, []).append({
            "trade_id": t.trade_id,
            "stake_usd": t.stake_usd,
            "result": t.result,
            "direction": t.result,  # placeholder if needed
            "session_id": t.session_id
        })

    return grouped


def load_features_by_user():
    features = {}
    path = Path(FEATURES_DIR)

    for file in path.glob("*.json"):
        with open(file, "r") as f:
            data = json.load(f)
            features[data["user_id"]] = data

    return features


# -----------------------------
# PIPELINE STAGE 1
# -----------------------------

def run_features(trades, news):
    engine = FeatureEngine(trades, news)
    results = engine.compute_all()
    write_features(FEATURES_DIR, results)
    return results


# -----------------------------
# PIPELINE STAGE 2
# -----------------------------

def run_patterns(features_by_user, trades_by_user):
    client = OpenAILLMClient()
    runner = ContractRunner(client)

    return run_pattern_detection(
        llm_runner=runner,
        features_by_user=features_by_user,
        trades_by_user=trades_by_user
    )


# -----------------------------
# MAIN PIPELINE
# -----------------------------

def main():

    print("\n=== INIT ===")

    trades = load_trades(TRADES_PATH)
    news = load_news(NEWS_PATH)

    print(f"Loaded {len(trades)} trades")
    print(f"Loaded {len(news)} news events")

    # -------------------------
    # STAGE 1: FEATURES
    # -------------------------
    print("\n=== FEATURES_COMPUTED ===")

    run_features(trades, news)

    # VALIDATE FEATURES (hard gate)
    print("\n=== FEATURES_VALIDATION ===")

    validation_result = validate_all_features()
    print(validation_result)

    # -------------------------
    # PREP FOR STAGE 2
    # -------------------------
    print("\n=== PREPARING PATTERN INPUTS ===")

    features_by_user = load_features_by_user()
    trades_by_user = group_trades_by_user(trades)

    # -------------------------
    # STAGE 2: PATTERNS
    # -------------------------
    print("\n=== PATTERN_DETECTION ===")

    pattern_results = run_patterns(features_by_user, trades_by_user)

    # PRINT OUTPUT
    print("\n=== PATTERN RESULTS ===")

    print(json.dumps(pattern_results, indent=2))

    print("\n=== PATTERN_VALIDATION ===")

    trades_dict_format = build_trades_dict(trades)

    validate_patterns_file(
        patterns_path="patterns.json",
        trades=trades_dict_format
    )

    print("Pattern validation OK")

    print("\n=== PIPELINE COMPLETE (up to stage 2) ===")

    print("\n=== RISK_SCORING ===")

    risk_results = compute_risk_scores(
        features_by_user,
        {p["user_id"]: p for p in pattern_results}
    )

    save_risk_scores(risk_results)

    print("\n=== INTEGRITY_CHECKS ===")

    integrity_results = run_integrity_checks(
        features_by_user,
        {p["user_id"]: p for p in pattern_results},
        {r["user_id"]: r for r in risk_results}
    )

    print(json.dumps(integrity_results, indent=2))

    print(json.dumps(risk_results, indent=2))


    print("\n=== INTERVENTION_PLANNING ===")

    client = OpenAILLMClient()
    runner = ContractRunner(client)

    interventions = run_intervention_planning(
        runner,
        features_by_user,
        {p["user_id"]: p for p in pattern_results},
        {r["user_id"]: r for r in risk_results}
    )

    save_interventions(interventions)

    print(json.dumps(interventions, indent=2))

    print("\n=== INTERVENTION_VALIDATION ===")

    intervention_validation = validate_all_interventions(
        interventions,
        {p["user_id"]: p for p in pattern_results},
        {r["user_id"]: r for r in risk_results}
    )

    print(intervention_validation)

def build_trades_dict(trades):
    """
    Converts Trade objects into validation-friendly dicts.
    """
    return [{
        "trade_id": t.trade_id,
        "user_id": t.user_id,
        "open_ts": t.open_ts,
        "close_ts": t.close_ts,
        "stake_usd": t.stake_usd,
        "payout_usd": t.payout_usd,
        "result": t.result,
        "session_id": t.session_id
    } for t in trades]


if __name__ == "__main__":
    main()