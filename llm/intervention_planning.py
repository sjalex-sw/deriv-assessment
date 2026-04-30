INTERVENTION_TYPES = [
    "soft_nudge",
    "deposit_limit_prompt",
    "cooling_off_period",
    "human_outreach"
]

import json
from typing import Dict, List


def build_stage2_prompt(features_by_user, patterns_by_user, risk_by_user):
    """
    Single consolidated prompt for all users.
    """

    payload = []

    for user_id in features_by_user:

        payload.append({
            "user_id": user_id,
            "features": features_by_user[user_id],
            "patterns": patterns_by_user.get(user_id, {}).get("patterns", []),
            "risk": risk_by_user[user_id]
        })

    return f"""
You are a responsible trading intervention system.

You MUST:
- Use ONLY provided data
- Do NOT infer missing behavior
- Do NOT hallucinate patterns
- Do NOT change risk tiers

Allowed intervention types:
{", ".join(INTERVENTION_TYPES)}

For each user, generate exactly ONE intervention.

DATA:
{json.dumps(payload, indent=2)}

OUTPUT REQUIREMENTS:
Return a JSON array.
Each item must match the schema exactly.
"""

INTERVENTION_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": [
            "user_id",
            "risk_tier",
            "intervention_type",
            "triggering_patterns",
            "evidence_summary",
            "recommended_action"
        ],
        "properties": {
            "user_id": {"type": "string"},
            "risk_tier": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"]
            },
            "intervention_type": {
                "type": "string",
                "enum": INTERVENTION_TYPES
            },
            "triggering_patterns": {
                "type": "array",
                "items": {"type": "string"}
            },
            "evidence_summary": {"type": "string"},
            "recommended_action": {"type": "string"}
        }
    }
}

from llm.contract import PromptContract


def run_intervention_planning(llm_runner, features_by_user, patterns_by_user, risk_by_user):

    contract = PromptContract(
        stage="INTERVENTION_PLANNING",
        system_prompt="""
SYSTEM:
You generate structured JSON only.

If unsure:
- still output valid JSON
- never output error messages
- never output explanation text
- never deviate from schema

You are a strict JSON generator for responsible trading interventions.

Rules:
- Output must match schema exactly
- Use only provided data
- No additional commentary
- No extra keys

Example output:

[
  {
    "user_id": "u_001",
    "risk_tier": "high",
    "intervention_type": "cooling_off_period",
    "triggering_patterns": ["martingale"],
    "evidence_summary": "Repeated stake escalation after losses",
    "recommended_action": "Suggest 24h cooling off period"
  }
]
""",
        user_prompt=build_stage2_prompt(
            features_by_user,
            patterns_by_user,
            risk_by_user
        ),
        schema=INTERVENTION_SCHEMA,
        output_path="interventions.json",
        user_id=None,
        input_files=[
            "features/",
            "patterns.json",
            "risk_scores.json"
        ],
        temperature=0.2
    )

    return llm_runner.run(contract)

import json
from pathlib import Path

def save_interventions(data, path="interventions.json"):
    Path(path).write_text(json.dumps(data, indent=2))