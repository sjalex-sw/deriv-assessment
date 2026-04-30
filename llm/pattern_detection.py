import json
from typing import List, Dict, Any
from pathlib import Path

from llm.contract import PromptContract, ContractRunner
from pipeline.schemas_json import PATTERN_SCHEMA


# -----------------------------
# CONTROLLED VOCABULARY
# -----------------------------

PATTERN_VOCAB = [
    "martingale",
    "anti_martingale",
    "revenge_trading",
    "news_chasing",
    "scalping",
    "position_doubling",
    "normal",
    "insufficient_evidence"
]


# -----------------------------
# FEATURE FORMATTING
# -----------------------------

def format_features(features: Dict[str, Any]) -> str:
    """
    Compact deterministic serialization for LLM input.
    """
    keys = sorted(features.keys())
    return "\n".join(f"{k}: {features[k]}" for k in keys)


# -----------------------------
# TRADE COMPRESSION (LAST 30)
# -----------------------------

def compress_trades(trades: List[Dict[str, Any]]) -> str:
    """
    Convert last 30 trades into compact deterministic format.
    """
    lines = []

    for t in trades[-30:]:
        line = (
            f"{t['trade_id']} | "
            f"stake={t['stake_usd']} | "
            f"result={t['result']} | "
            f"dir={t['direction']} | "
            f"session={t['session_id']}"
        )
        lines.append(line)

    return "\n".join(lines)


# -----------------------------
# SYSTEM PROMPT
# -----------------------------

SYSTEM_PROMPT = f"""
You are a strict JSON generator.

ABSOLUTE RULES:
- Output MUST match the schema exactly.
- "evidence" MUST be an array of OBJECTS.
- Each evidence item MUST have:
  - pattern (string)
  - triggering_features (array of strings)
  - trade_ids (array of strings)
  - explanation (string)

NEVER output:
- raw strings inside evidence
- trade IDs directly in evidence array
- any flattened structure

If you are unsure, still output valid schema JSON.

CONFIDENCE RULE:
- confidence MUST be ONE of: "low", "medium", "high"
- NEVER output numbers (e.g. 0.85, 0.7, 1.0)
- NEVER output probabilities
- NEVER output floats or scores

Examples:
GOOD:
"confidence": "high"

BAD:
"confidence": 0.85
"confidence": 0.7

Allowed patterns:
{", ".join(PATTERN_VOCAB)}
"""


# -----------------------------
# USER PROMPT BUILDER
# -----------------------------

def build_prompt(features: Dict, trades: List[Dict]) -> str:
    return f"""
FEATURE VECTOR:
{format_features(features)}

LAST 30 TRADES:
{compress_trades(trades)}

TASK:
Classify the trading behavior using one or more patterns from the allowed vocabulary.

Return:
- user_id
- patterns
- evidence with trade_ids
- confidence level
"""


# -----------------------------
# RUNNER
# -----------------------------

class PatternDetector:
    def __init__(self, llm_client: ContractRunner):
        self.llm = llm_client

    def classify_user(
        self,
        user_id: str,
        features: Dict[str, Any],
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        contract = PromptContract(
            stage="PATTERN_DETECTION",
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_prompt(features, trades),
            schema=PATTERN_SCHEMA,
            output_path=f"patterns/{user_id}.json",
            user_id=user_id,
            input_files=[
                f"features/{user_id}.json"
            ],
            temperature=0.2
        )

        return self.llm.run(contract)


# -----------------------------
# PIPELINE EXECUTION
# -----------------------------

def run_pattern_detection(
    llm_runner: ContractRunner,
    features_by_user: Dict[str, Dict],
    trades_by_user: Dict[str, List[Dict]]
):
    detector = PatternDetector(llm_runner)

    results = []

    for user_id in features_by_user.keys():

        result = detector.classify_user(
            user_id=user_id,
            features=features_by_user[user_id],
            trades=trades_by_user[user_id]
        )

        results.append(result)

    # Save combined file
    Path("patterns.json").write_text(json.dumps(results, indent=2))

    return results