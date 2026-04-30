from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime
import json
import os
from collections import defaultdict


# -----------------------------
# DATA MODEL (STRICT INPUT)
# -----------------------------

@dataclass
class Trade:
    user_id: str
    trade_id: str
    open_ts: datetime
    close_ts: datetime
    stake_usd: float
    payout_usd: float
    result: str  # "win" | "loss"
    session_id: str


# -----------------------------
# TIME UTILITIES (CRITICAL)
# -----------------------------

def parse_ts(ts: str) -> datetime:
    # ISO-8601 UTC assumed
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def seconds_between(t1: datetime, t2: datetime) -> float:
    return abs((t2 - t1).total_seconds())


# -----------------------------
# CORE ENGINE CLASS
# -----------------------------

class FeatureEngine:
    def __init__(self, trades: List[Trade], news_events: List[Dict[str, Any]]):
        self.trades = sorted(trades, key=lambda x: (x.user_id, x.open_ts))
        self.news_events = [
            {
                "time": parse_ts(n["datetime_utc"]),
                "impact": n["impact"]
            }
            for n in news_events
        ]

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def compute_all(self) -> Dict[str, Dict[str, Any]]:
        users = defaultdict(list)

        for t in self.trades:
            users[t.user_id].append(t)

        return {
            user_id: self._compute_user_features(user_id, user_trades)
            for user_id, user_trades in users.items()
        }

    # -------------------------
    # PER USER COMPUTATION
    # -------------------------
    def _compute_user_features(self, user_id: str, trades: List[Trade]) -> Dict[str, Any]:

        total_trades = len(trades)

        stakes = [t.stake_usd for t in trades]
        results = [t.result for t in trades]

        wins = sum(1 for r in results if r == "win")

        # -------------------------
        # 1. average stake
        # -------------------------
        avg_stake = sum(stakes) / total_trades if total_trades else 0

        # -------------------------
        # 2. stake escalation after losses
        # -------------------------
        escalation_ratios = []
        for i in range(1, total_trades):
            prev = trades[i - 1]
            curr = trades[i]

            if prev.result == "loss":
                if prev.stake_usd > 0:
                    escalation_ratios.append(curr.stake_usd / prev.stake_usd)

        stake_escalation_ratio = (
            sum(escalation_ratios) / len(escalation_ratios)
            if escalation_ratios else 0
        )

        # -------------------------
        # 3. trades per minute
        # -------------------------
        time_span = seconds_between(trades[0].open_ts, trades[-1].open_ts) / 60
        trades_per_minute = total_trades / time_span if time_span > 0 else 0

        # -------------------------
        # 4. news proximity %
        # -------------------------
        news_hits = 0

        for t in trades:
            for n in self.news_events:
                if abs(seconds_between(t.open_ts, n["time"])) <= 300:
                    news_hits += 1
                    break

        news_pct = (news_hits / total_trades) * 100 if total_trades else 0

        # -------------------------
        # 5. win rate
        # -------------------------
        win_rate = wins / total_trades if total_trades else 0

        # -------------------------
        # 6. revenge interval
        # -------------------------
        revenge_intervals = []

        for i in range(1, total_trades):
            if trades[i - 1].result == "loss":
                interval = seconds_between(
                    trades[i - 1].open_ts,
                    trades[i].open_ts
                )
                revenge_intervals.append(interval)

        revenge_interval = (
            sum(revenge_intervals) / len(revenge_intervals)
            if revenge_intervals else 0
        )

        # -------------------------
        # 7. longest losing streak
        # -------------------------
        max_streak = 0
        current = 0

        for t in trades:
            if t.result == "loss":
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0

        # -------------------------
        # 8. net profit/loss
        # -------------------------
        net_pnl = sum(t.payout_usd - t.stake_usd for t in trades)

        # -------------------------
        # 9. session duration
        # -------------------------
        sessions = defaultdict(list)

        for t in trades:
            sessions[t.session_id].append(t)

        session_durations = []

        for s_trades in sessions.values():
            start = min(t.open_ts for t in s_trades)
            end = max(t.close_ts for t in s_trades)
            session_durations.append(seconds_between(start, end))

        avg_session_duration = (
            sum(session_durations) / len(session_durations)
            if session_durations else 0
        )

        # -------------------------
        # AUDIT METADATA (IMPORTANT)
        # -------------------------
        audit = {
            "trade_count": total_trades,
            "session_count": len(sessions),
            "win_count": wins,
            "loss_count": total_trades - wins,
            "escalation_samples": len(escalation_ratios),
            "revenge_samples": len(revenge_intervals)
        }

        # -------------------------
        # FINAL OUTPUT
        # -------------------------
        return {
            "user_id": user_id,

            "average_stake": avg_stake,
            "stake_escalation_ratio_after_losses": stake_escalation_ratio,
            "trades_per_minute": trades_per_minute,
            "news_trade_percentage": news_pct,
            "win_rate": win_rate,
            "revenge_interval_seconds": revenge_interval,
            "longest_losing_streak": max_streak,
            "total_trades": total_trades,
            "net_profit_loss": net_pnl,
            "avg_session_duration_seconds": avg_session_duration,

            "supporting_stats": audit
        }


# -----------------------------
# WRITER
# -----------------------------

def write_features(output_dir: str, results: Dict[str, Dict[str, Any]]):
    os.makedirs(output_dir, exist_ok=True)

    for user_id, features in results.items():
        path = os.path.join(output_dir, f"{user_id}.json")

        with open(path, "w") as f:
            json.dump(features, f, indent=2)