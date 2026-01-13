# AI Sell Strategy Design

**Date:** 2026-01-12
**Status:** Approved

## Overview

An AI-powered sell decision system that monitors all open positions and intelligently decides when to exit. Instead of blindly copying whale sells or using rigid rules, the AI evaluates each position using price action, whale behavior, and market context to make smart exit decisions.

### Core Behavior

- **Copies whale BUYs** (existing behavior, unchanged)
- **AI decides SELLs** (new) - evaluates whether to exit based on multiple signals
- **Conservative default** - when uncertain, AI defaults to conservative thresholds (+10% take profit, -15% stop loss)
- **Can go aggressive** - when confident, AI can hold for bigger gains (+20-50%)

### User Configuration

Each user can set their risk profile:
- **Conservative**: Quick profits, tight stops
- **Moderate**: Balanced risk/reward
- **Aggressive**: Hold for big wins, wider stops

Default is "maximize profit" but the AI adapts based on user preference.

### Evaluation Frequency

Adaptive checking:
- Stable markets: Every 30 minutes
- Volatile/near resolution: Every 5 minutes
- Whale activity detected: Immediate evaluation

---

## Technical Architecture

### Where the AI Lives

The AI sell logic integrates into the existing `bot-service/main.py`. We add a new evaluation loop that runs alongside the existing whale-copy loop:

```
Existing: poll_whale_trades() → copy BUYs → save to DB
New:      evaluate_positions() → AI decides → execute SELLs
```

### Components

1. **Position Evaluator** - Gathers all open positions and enriches them with current data
2. **Signal Collector** - Fetches price data, whale activity, market context for each position
3. **AI Decision Engine** - Calls Claude API with position + signals, gets sell/hold decision
4. **Execution Handler** - Records sell decisions, updates PnL, sends notifications

### Data Flow

```
Every X minutes (adaptive):
  1. Get all open positions from DB
  2. For each position:
     - Fetch current price
     - Check whale's current position (still holding? sold?)
     - Get market metadata (resolution date, volume, etc.)
  3. Build context prompt for Claude
  4. Claude returns: { action: "SELL" | "HOLD", reasoning: "...", confidence: 0.85 }
  5. If SELL: record trade, update PnL, notify user
  6. Store reasoning in DB for user review
```

### Cost Control

- Batch similar positions in one API call when possible
- Skip evaluation if nothing changed since last check
- Use `claude-3-haiku` for routine checks, `claude-sonnet` for high-stakes decisions

---

## Database Changes

### New Table: `ai_evaluations`

Stores every AI decision for transparency and debugging:

```sql
CREATE TABLE ai_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  trade_id INTEGER REFERENCES trades(id),
  action TEXT NOT NULL CHECK (action IN ('HOLD', 'SELL')),
  reasoning TEXT NOT NULL,
  confidence DECIMAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  signals JSONB NOT NULL,
  strategy_used TEXT NOT NULL CHECK (strategy_used IN ('conservative', 'moderate', 'aggressive')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying user's AI history
CREATE INDEX idx_ai_evaluations_user_id ON ai_evaluations(user_id, created_at DESC);
```

**Signals JSONB structure:**
```json
{
  "current_price": 0.72,
  "entry_price": 0.65,
  "pnl_percent": 10.7,
  "whale_status": "holding",
  "market_resolution_date": "2026-03-01",
  "volatility_score": "medium"
}
```

### Profile Updates

```sql
ALTER TABLE profiles ADD COLUMN ai_risk_profile TEXT DEFAULT 'maximize_profit'
  CHECK (ai_risk_profile IN ('conservative', 'moderate', 'aggressive', 'maximize_profit'));

ALTER TABLE profiles ADD COLUMN ai_enabled BOOLEAN DEFAULT true;

ALTER TABLE profiles ADD COLUMN ai_custom_instructions TEXT DEFAULT
'- Never sell within the first hour of buying
- I''m bullish on crypto markets, hold longer on those
- If a position is down but whale is adding, always hold
- Take profits quickly on short-term (<7 day) markets';
```

### Trades Table Updates

```sql
ALTER TABLE trades ADD COLUMN sell_reasoning TEXT;
ALTER TABLE trades ADD COLUMN ai_initiated BOOLEAN DEFAULT false;
```

---

## AI Prompt Structure

### What We Send to Claude

```
You are a trading assistant for Polymarket prediction markets.

USER PROFILE:
- Risk preference: {maximize_profit | conservative | moderate | aggressive}
- Default thresholds: +10% take profit, -15% stop loss (conservative baseline)

CUSTOM INSTRUCTIONS (from user):
{user's custom instructions from profile}

POSITION:
- Market: "Will Bitcoin hit $100k by March 2026?"
- Side: YES
- Entry price: $0.65
- Current price: $0.72
- Unrealized PnL: +10.7%
- Position size: $50
- Held for: 2 days

WHALE STATUS:
- Whale still holding: YES
- Whale's entry: $0.62
- Whale added to position: NO
- Whale sold any: NO

MARKET CONTEXT:
- Resolution date: 45 days away
- 24h volume: $125,000
- Price trend (24h): +3.2%
- Volatility: Medium

DECISION REQUIRED:
Should we SELL or HOLD? Consider the user's risk preference and custom instructions.
Return JSON: { "action": "SELL" | "HOLD", "reasoning": "...", "confidence": 0.0-1.0, "strategy": "conservative|moderate|aggressive" }
```

### Claude Returns

```json
{
  "action": "HOLD",
  "reasoning": "Position is +10.7% which hits conservative take-profit, but user wants to maximize profit. Whale still holding with conviction, market has 45 days to run, momentum is positive. Holding for moderate target of +20%.",
  "confidence": 0.78,
  "strategy": "moderate"
}
```

---

## Notifications & UI

### Brief Notifications (Dashboard)

When AI sells, user sees a toast/alert:
```
✅ Sold "BTC hits $100k" — +15.2% profit
   AI: Whale exited, took profit before momentum fades
```

### Trade History

Each trade row shows:
- 🤖 icon if AI-initiated (vs whale-copy)
- Brief reasoning in expandable row
- Click to see full AI reasoning from `ai_evaluations`

### New Settings Section

```
AI Trading Settings
├── Enable AI Sells: [Toggle ON/OFF]
├── Risk Profile: [Dropdown: Maximize Profit ▼]
├── Custom Instructions: [Textarea with defaults]
└── View AI Decision Log: [Link to history]
```

### AI Decision Log Page

Table showing all AI evaluations:
- Position | Action | Reasoning | Confidence | Time
- Filter by SELL/HOLD
- See what signals the AI was looking at

---

## Error Handling & Edge Cases

### API Failures

If Claude API is down or times out:
- **Don't sell** - hold is the safe default
- Log the failure, retry in 5 minutes
- If 3+ consecutive failures: alert user "AI evaluation paused"
- Fall back to conservative rule-based thresholds only if user opts in

### Market Resolution

When a market resolves (outcome decided):
- Skip AI evaluation, mark position as resolved
- Calculate final PnL based on resolution (YES = $1.00, NO = $0.00)
- No sell needed - Polymarket handles payout

### Whale Wallet Issues

If we can't fetch whale's current position:
- Treat as "whale status unknown"
- AI makes decision based on price + market context only
- Note in reasoning: "Whale data unavailable"

### Rapid Price Movement

If price moves >10% since last check:
- Trigger immediate evaluation regardless of schedule
- Flag as "high urgency" in prompt so AI knows to act decisively

### Conflicting Signals

When signals contradict (e.g., price up but whale sold):
- This is exactly what the AI is for
- Confidence score reflects uncertainty
- If confidence < 0.5, default to HOLD

### User Has AI Disabled

- Skip all AI evaluation for that user
- Their positions just sit (current behavior)
- They can manually sell via dashboard if we add that later

---

## Implementation Phases

### Phase 1: Database & Settings
- Add `ai_evaluations` table
- Add new columns to `profiles` and `trades`
- Add AI settings UI to dashboard (toggle, risk profile, custom instructions)
- No AI logic yet - just the foundation

### Phase 2: Signal Collection
- Build signal collector: current price, whale status, market context
- Fetch whale's current position from Polymarket API
- Calculate volatility and momentum scores
- Test that we're gathering accurate data

### Phase 3: AI Decision Engine
- Integrate Claude API into bot-service
- Build prompt constructor with all signals
- Parse AI response, validate JSON structure
- Log all evaluations to `ai_evaluations` table

### Phase 4: Adaptive Scheduling
- Implement adaptive check frequency
- Stable = 30min, volatile = 5min, whale activity = immediate
- Add event triggers for whale sells and big price moves

### Phase 5: Execution & Notifications
- Execute AI sell decisions (update trades, calculate realized PnL)
- Send brief notifications to dashboard
- Show AI reasoning in trade history
- Add AI decision log page

### Phase 6: Testing & Tuning
- Run in "shadow mode" first (AI decides but doesn't execute)
- Compare AI decisions vs actual outcomes
- Tune prompts based on results
