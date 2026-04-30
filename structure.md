Here’s a clean implementation blueprint. This is structured like a real production pipeline, not a notebook script.

---

# 0. High-level architecture (don’t skip this)

Split the system into 5 deterministic modules + 1 LLM layer:

```
/pipeline
  /ingest
  /features
  /patterns
  /risk
  /interventions
  /audit
  /utils
  /llm
```

Core rule:

* Everything before `/llm` is deterministic.
* LLM only *labels + explains*, never computes metrics or scores.

---

# 1. Data ingestion + dataset expansion

## 1.1 Loader (`ingest/loader.py`)

Read:

* `trades.json`
* `economic_calendar.json`

Normalize into:

```python
Trade:
  user_id
  trade_id
  open_ts (datetime)
  close_ts (datetime)
  stake_usd
  result
  session_id
```

Also:

* sort trades by `user_id + open_ts`

---

## 1.2 Synthetic expansion (mandatory)

If < 8 users or < 800 trades:

Create `ingest/synth.py`:

Rules:

* preserve schema exactly
* generate:

  * random sessions (5–30 trades each)
  * realistic time spacing (20s–10min)
  * correlated behavior patterns:

    * martingale users: stake multiplier after loss
    * scalpers: < 2 min trades
    * revenge traders: fast re-entry after loss

Output:

* merged dataset in memory (do NOT overwrite original files)

---

## Output artifact:

```
data/normalized_trades.json
```

---

# 2. Feature Engineering (STRICTLY deterministic)

Folder:

```
/features/engine.py
/features/writer.py
```

---

## 2.1 Required computations per user

You MUST compute using raw trade sequences only.

---

### A. average stake

```python
avg_stake = sum(stake) / n_trades
```

---

### B. stake escalation ratio after losses

Definition:

* ratio = stake_after_loss / stake_before_loss
* averaged over all loss→next trade transitions

---

### C. trades per minute

```python
(total_trades) / (last_trade_time - first_trade_time in minutes)
```

---

### D. news proximity %

For each trade:

* if abs(trade_time - news_event_time) <= 5 min → count

---

### E. win rate

```python
wins / total
```

---

### F. revenge interval

For every loss:

* time to next trade

average it

---

### G. longest losing streak

Single scan over ordered trades.

---

### H. total net P/L

```python
sum(payout - stake)
```

---

### I. session duration

Per session:

* max(close) - min(open)
  then average across sessions

---

## Output format per user:

```
features/u_001.json
```

Include:

```json
{
  "user_id": "u_001",
  "features": {...},
  "supporting_stats": {
    "trade_count": 120,
    "loss_count": 70,
    "session_count": 12
  }
}
```

---

# 3. Pattern Detection (LLM stage 1)

Folder:

```
/llm/pattern_classifier.py
```

---

## Input to LLM

For each user:

### Include:

* full feature vector
* last 30 trades (compressed):

```text
t1: stake=10, result=loss, gap=32s
t2: stake=20, result=loss, gap=25s
```

* definitions of patterns (VERY IMPORTANT)

---

## Controlled vocabulary enforcement

You MUST enforce:

* output must be subset of:

```
martingale
anti_martingale
revenge_trading
news_chasing
scalping
position_doubling
normal
insufficient_evidence
```

---

## Prompt constraint (important)

Force:

* “use ONLY provided features”
* “cite trade_ids for evidence”
* “do NOT compute metrics”

---

## Output

Save:

```
patterns.json
```

---

# 4. Deterministic Risk Scoring (NO LLM)

Folder:

```
/risk/model.py
```

---

## 4.1 Core idea

Risk score = weighted sum of normalized features + pattern multipliers

---

## 4.2 Base formula

```python
risk = 0
```

---

### Pattern weights

```python
martingale: +25
revenge_trading: +20
position_doubling: +25
scalping: +10
news_chasing: +15
normal: 0
```

---

### Feature contributions

Normalize each 0–1:

* stake escalation → *30 weight
* revenge interval (inverse) → *15
* losing streak → *20
* news proximity → *10
* net loss severity → *20
* trade frequency → *5

---

## 4.3 Final clamp

```python
risk = min(100, max(0, risk))
```

---

## 4.4 Tiering

```python
0–25   low
26–50  medium
51–75  high
76–100 critical
```

---

## Output:

```
risk_scores.json
risk_model.md
```

---

# 5. Intervention Planning (LLM stage 2)

Folder:

```
/llm/intervention_planner.py
```

---

## Input to LLM

Provide:

* all users
* patterns.json
* risk_scores.json
* feature summaries

---

## Hard constraint

LLM MUST NOT:

* change risk scores
* invent metrics
* ignore evidence

---

## Output schema

For each user:

```json
{
  "user_id": "...",
  "risk_tier": "...",
  "intervention_type": "...",
  "triggering_patterns": [],
  "evidence_summary": "...",
  "recommended_action": "..."
}
```

---

## Intervention mapping logic (guidance)

* low → soft_nudge
* medium → deposit_limit_prompt
* high → cooling_off_period
* critical → human_outreach

---

## Save:

```
interventions.json
```

---

# 6. False Positive Audit (deterministic)

Folder:

```
/audit/martingale_check.py
```

---

## Logic

For users labeled martingale:

Check:

```
for each loss:
    next_trade.stake > previous_stake
```

If consistent escalation ≥ threshold (e.g. 70% transitions):

→ verified = true

---

## Output:

```
false_positive_audit.json
```

---

# 7. Cohort Insights (deterministic analytics only)

Folder:

```
/analytics/cohort.py
```

---

## Examples:

### A. news exposure vs loss rate

Group:

* trades within 5 min of news
* others

Compute:

* loss_rate difference

---

### B. revenge interval vs escalation

Correlation:

* stake escalation
* revenge interval

---

## Output:

```
cohort_insights.json
```

---

# 8. Logging ALL LLM calls

Folder:

```
/llm/logger.py
```

---

Each call logs:

* stage
* user_id
* timestamp
* model
* prompt hash
* input files
* output file

Append-only:

```
llm_calls.jsonl
```

---

# 9. Pipeline Orchestrator

Single entry point:

```
main.py
```

Pipeline order MUST enforce:

```
INIT
→ INPUTS_LOADED
→ DATASET_EXTENDED_OR_VALIDATED
→ FEATURES_COMPUTED
→ PATTERNS_CLASSIFIED
→ RISK_SCORES_COMPUTED
→ INTERVENTIONS_GENERATED
→ VALIDATION_COMPLETE
→ RESULTS_FINALISED
```

Hard rule:

* each stage writes a marker file:

  ```
  state/FEATURES_COMPUTED.done
  ```

---

# 10. Validation system (critical for evaluator)

```
validate.py
```

Checks:

### Structure

* all artifacts exist

### Determinism

* re-run risk scoring twice → identical hash

### Dependency correctness

* features exist before patterns
* patterns exist before risk

### Integrity

* interventions reference valid users
* patterns reference valid trades

### Required behavior

* u_001 must show martingale or position_doubling

---

# 11. Key design mistakes to avoid (important)

Do NOT:

* let LLM compute averages or ratios
* compute risk in prompts
* skip intermediate artifacts
* overwrite raw data
* allow unordered trade processing
* mix feature + pattern logic

---

# 12. Minimal execution flow

```
load data
→ expand dataset
→ compute features (write files)
→ classify patterns (LLM)
→ compute risk scores (pure code)
→ generate interventions (LLM)
→ run audits
→ run validation
```

---

If you want, I can next give:

* exact folder tree
* sample prompts for both LLM stages
* or a reference implementation skeleton in Python

Just say which.
