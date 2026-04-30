PATTERN_SCHEMA = {
    "type": "object",
    "required": ["user_id", "patterns", "evidence", "confidence"],
    "properties": {
        "user_id": {"type": "string"},

        "patterns": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "martingale",
                    "anti_martingale",
                    "revenge_trading",
                    "news_chasing",
                    "scalping",
                    "position_doubling",
                    "normal",
                    "insufficient_evidence"
                ]
            }
        },

        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pattern", "triggering_features", "trade_ids", "explanation"],
                "properties": {
                    "pattern": {"type": "string"},
                    "triggering_features": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "trade_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "explanation": {"type": "string"}
                }
            }
        },

        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"]
        }
    }
}


INTERVENTION_SCHEMA = {
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
            "enum": [
                "soft_nudge",
                "deposit_limit_prompt",
                "cooling_off_period",
                "human_outreach"
            ]
        },

        "triggering_patterns": {
            "type": "array",
            "items": {"type": "string"}
        },

        "evidence_summary": {"type": "string"},
        "recommended_action": {"type": "string"}
    }
}