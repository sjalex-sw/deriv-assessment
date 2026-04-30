# Risk Model v1.0

Risk Score = weighted sum of normalized behavioral signals

Score range: 0–100

---

## Pattern Weights

- martingale: 25
- position_doubling: 20
- revenge_trading: 20
- news_chasing: 15
- scalping: 10
- anti_martingale: -10
- normal: 0
- insufficient_evidence: 0

---

## Feature Contributions

All normalized to [0,1] before weighting.

- stake_escalation_after_losses: weight 20
- rapid_trade_frequency: weight 15
- news_trade_percentage: weight 15
- longest_losing_streak: weight 15
- net_loss_severity: weight 20
- revenge_activity_score: weight 15

---

## Final Formula

risk_score =
min(100,
    pattern_score +
    feature_score
)