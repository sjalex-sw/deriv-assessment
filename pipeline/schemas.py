from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Optional
from datetime import datetime


# ---------------------------
# 1. FEATURES
# ---------------------------

class UserFeatures(BaseModel):
    user_id: str

    average_stake: float
    stake_escalation_ratio_after_losses: float
    trades_per_minute: float
    news_trade_percentage: float
    win_rate: float
    revenge_interval_seconds: float
    longest_losing_streak: int
    total_trades: int
    net_profit_loss: float
    avg_session_duration_seconds: float

    supporting_stats: Dict[str, float | int]


# ---------------------------
# 2. PATTERNS (LLM OUTPUT)
# ---------------------------

PatternLabel = Literal[
    "martingale",
    "anti_martingale",
    "revenge_trading",
    "news_chasing",
    "scalping",
    "position_doubling",
    "normal",
    "insufficient_evidence"
]


class PatternEvidence(BaseModel):
    pattern: PatternLabel
    triggering_features: List[str]
    trade_ids: List[str]
    explanation: str


class UserPatternClassification(BaseModel):
    user_id: str
    patterns: List[PatternLabel]
    evidence: List[PatternEvidence]
    confidence: Literal["low", "medium", "high"]


# ---------------------------
# 3. RISK SCORES (deterministic)
# ---------------------------

RiskTier = Literal["low", "medium", "high", "critical"]


class RiskScore(BaseModel):
    user_id: str
    risk_score: float = Field(ge=0, le=100)
    risk_tier: RiskTier
    contributing_factors: Dict[str, float]
    formula_version: str


# ---------------------------
# 4. INTERVENTIONS (LLM OUTPUT)
# ---------------------------

InterventionType = Literal[
    "soft_nudge",
    "deposit_limit_prompt",
    "cooling_off_period",
    "human_outreach"
]


class Intervention(BaseModel):
    user_id: str
    risk_tier: RiskTier
    intervention_type: InterventionType
    triggering_patterns: List[str]
    evidence_summary: str
    recommended_action: str


# ---------------------------
# 5. AUDIT
# ---------------------------

class MartingaleAudit(BaseModel):
    user_id: str
    pattern: Literal["martingale"]
    verified: bool
    supporting_trade_sequence: List[str]
    calculation: str