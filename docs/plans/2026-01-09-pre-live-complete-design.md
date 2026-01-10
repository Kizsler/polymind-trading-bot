# PolyMind Pre-Live Complete Design

**Date:** 2026-01-09
**Status:** Approved
**Scope:** Everything needed before going live (paper trading until wallet added)

---

## Overview

Complete the PolyMind trading bot with all features from the PRD:
1. Live execution infrastructure (dormant until wallet configured)
2. Wallet intelligence (scoring, per-wallet controls)
3. Market intelligence (quality scoring, allow/deny lists)
4. External integrations (Kalshi, Binance, arbitrage detection)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTERNAL DATA SOURCES                       │
├──────────────────┬──────────────────┬───────────────────────────┤
│  Polymarket API  │   Kalshi API     │   Binance WebSocket       │
│  (existing)      │   (new)          │   (new)                   │
└────────┬─────────┴────────┬─────────┴─────────────┬─────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MARKET INTELLIGENCE                           │
│  • Liquidity scoring    • Cross-platform price comparison       │
│  • Volatility tracking  • Arbitrage opportunity detection       │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    WALLET INTELLIGENCE                           │
│  • Performance scoring   • Win rate / ROI tracking              │
│  • Per-wallet controls   • Trade size scaling                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              AI DECISION BRAIN (existing, enhanced)              │
│  Now receives: wallet scores, market quality, arb opportunities │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION ENGINE                              │
│  ┌─────────────┐    ┌─────────────┐                             │
│  │ PaperExec   │ OR │ LiveExec    │  ← Selected by mode         │
│  │ (existing)  │    │ (new)       │                             │
│  └─────────────┘    └─────────────┘                             │
│  • Slippage protection  • Retry logic  • Partial fill handling  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Live Execution Infrastructure

### 1.1 LiveExecutor
**File:** `src/polymind/core/execution/live.py`

Wraps Polymarket CLOB API for real order submission:
- Methods: `execute_order()`, `cancel_order()`, `get_order_status()`
- Returns same `ExecutionResult` as PaperExecutor
- Inactive until wallet credentials are configured (raises error if called without creds)

### 1.2 Slippage Protection
Before submitting any order:
- Fetch current orderbook
- Calculate expected fill price vs limit price
- Reject if slippage exceeds configured threshold (e.g., 2%)
- Applies to BOTH paper and live executors

### 1.3 Order Manager
**File:** `src/polymind/core/execution/manager.py`

- Handles retry logic (configurable attempts, backoff)
- Tracks partial fills and decides whether to chase remainder
- Manages order lifecycle: pending → filled/partial/failed/cancelled
- Stores order state in Redis for crash recovery

### 1.4 Execution Mode Switch
Setting `mode: "paper" | "live"` determines which executor is used. The `DecisionBrain` orchestrator selects the right one at runtime. Switching modes is instant - no restart required.

### 1.5 Safety Guards
- Live mode requires: wallet credentials present + explicit confirmation flag
- First-time live mode shows warning and requires acknowledgment
- Emergency kill switch stops all pending orders immediately

---

## Phase 2: Wallet Intelligence

### 2.1 Wallet Performance Tracker
**File:** `src/polymind/core/intelligence/wallet.py`

Tracks per-wallet metrics:
- **Win rate**: % of trades that were profitable
- **ROI**: Average return on investment per trade
- **Timing efficiency**: How early they enter before price moves
- **Drawdown behavior**: How they handle losing streaks
- **Market selection**: Which categories they trade

### 2.2 Wallet Confidence Score
Single 0.0–1.0 score:
```python
confidence = (
    win_rate * 0.3 +
    roi_normalized * 0.3 +
    timing_score * 0.2 +
    consistency * 0.2
)
```
Weights are configurable. AI Decision Brain receives this score as context.

### 2.3 Per-Wallet Controls
Stored in database per wallet:
- `enabled`: bool - whether to copy this wallet
- `scale_factor`: float - trade size multiplier (0.5 = half size, 2.0 = double)
- `max_trade_size`: float - cap regardless of their trade size
- `min_confidence`: float - skip if wallet score drops below threshold

### 2.4 Auto-Disable Logic
Automatically disable wallets that:
- Drop below confidence threshold for N consecutive days
- Hit a drawdown limit (e.g., -20% over 7 days)
- Go inactive for configurable period

---

## Phase 3: Market Intelligence

### 3.1 Market Analyzer
**File:** `src/polymind/core/intelligence/market.py`

For each market, calculates:
- **Liquidity depth**: Total $ available within 2% of current price
- **Bid/ask spread**: Current spread as percentage
- **Volatility**: Price movement over last 24h/7d
- **Time decay**: How close to resolution
- **Volume**: Recent trading volume

### 3.2 Market Quality Score
Single 0.0–1.0 score:
```python
quality = (
    liquidity_score * 0.35 +
    spread_score * 0.25 +
    volume_score * 0.20 +
    time_decay_score * 0.20
)
```
Low quality markets (< 0.3) are auto-rejected.

### 3.3 Allow/Deny Lists
Configurable market filters:
- **Category allowlist**: Only trade politics, crypto, etc.
- **Category denylist**: Never trade sports, entertainment
- **Specific market IDs**: Explicitly allow or block individual markets
- **Keyword filters**: Block markets containing certain terms

### 3.4 Price Caching
- Cache orderbook snapshots in Redis (5-second TTL)
- Reduces API calls when multiple signals hit same market
- Invalidate on trade execution

---

## Phase 4: External Integrations

### 4.1 Kalshi Client
**File:** `src/polymind/data/kalshi/client.py`

- REST API client for Kalshi's public endpoints
- Methods: `get_markets()`, `get_orderbook()`, `get_positions()`
- Read-only initially for arbitrage detection
- Credential-optional: works without API key for public data

### 4.2 Binance WebSocket Feed
**File:** `src/polymind/data/binance/feed.py`

- WebSocket connection to Binance price streams
- Subscribe to relevant symbols: BTC, ETH, SOL, etc.
- Maintains real-time price cache in Redis
- Auto-reconnect on disconnect

### 4.3 Market Normalizer
**File:** `src/polymind/core/intelligence/normalizer.py`

Maps equivalent markets across platforms:
- Polymarket "BTC above $100k by March" ↔ Kalshi equivalent
- Converts all odds to implied probability (0.0–1.0)
- Handles different market structures (binary vs. ranged)

### 4.4 Arbitrage Detector
**File:** `src/polymind/core/intelligence/arbitrage.py`

- Compares normalized prices across platforms
- Flags opportunities where spread exceeds threshold (e.g., 3%)
- Calculates expected profit after fees
- Sends signal to AI Decision Brain as "arbitrage" signal type

### 4.5 Price Lag Detector
Compares Binance real-time prices to Polymarket crypto markets:
- BTC hits $105k on Binance → check "BTC above $105k" market odds
- If market hasn't reacted, flag opportunity
- Configurable reaction time threshold

---

## Database Additions

### New Tables

```sql
-- Wallet performance metrics
CREATE TABLE wallet_metrics (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42) NOT NULL,
    win_rate FLOAT,
    roi FLOAT,
    timing_score FLOAT,
    consistency FLOAT,
    confidence_score FLOAT,
    total_trades INT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Per-wallet controls
ALTER TABLE wallets ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE wallets ADD COLUMN scale_factor FLOAT DEFAULT 1.0;
ALTER TABLE wallets ADD COLUMN max_trade_size FLOAT;
ALTER TABLE wallets ADD COLUMN min_confidence FLOAT DEFAULT 0.0;

-- Market filters
CREATE TABLE market_filters (
    id SERIAL PRIMARY KEY,
    filter_type VARCHAR(20) NOT NULL, -- 'category_allow', 'category_deny', 'market_id', 'keyword'
    value VARCHAR(255) NOT NULL,
    action VARCHAR(10) NOT NULL, -- 'allow' or 'deny'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Cross-platform market mappings
CREATE TABLE market_mappings (
    id SERIAL PRIMARY KEY,
    polymarket_id VARCHAR(255),
    kalshi_id VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Order tracking
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255),
    signal_id INT REFERENCES trades(id),
    status VARCHAR(20), -- 'pending', 'filled', 'partial', 'failed', 'cancelled'
    requested_size FLOAT,
    filled_size FLOAT,
    requested_price FLOAT,
    filled_price FLOAT,
    attempts INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Dashboard Additions

1. **Wallet Detail Page**
   - Performance charts (win rate, ROI over time)
   - Per-wallet settings controls
   - Trade history for this wallet

2. **Market Filters Page**
   - Manage allow/deny lists
   - Add/remove category filters
   - Keyword filter management

3. **Arbitrage View**
   - Live cross-platform opportunities
   - Historical arbitrage trades
   - Profit/loss by strategy

4. **Order History**
   - Full order lifecycle visibility
   - Partial fills, retries, failures
   - Filter by status

---

## File Summary

| Phase | New Files |
|-------|-----------|
| Execution | `core/execution/live.py`, `core/execution/manager.py`, `core/execution/slippage.py`, `core/execution/safety.py` |
| Wallet Intel | `core/intelligence/wallet.py`, `core/intelligence/scoring.py` |
| Market Intel | `core/intelligence/market.py`, `core/intelligence/filters.py` |
| External | `data/kalshi/client.py`, `data/binance/feed.py`, `core/intelligence/normalizer.py`, `core/intelligence/arbitrage.py`, `core/intelligence/pricelag.py` |

**Total:** ~15-20 new files, ~3000-4000 lines of code

---

## Success Criteria

- [ ] Can switch between paper/live mode without restart
- [ ] Wallet confidence scores visible in dashboard
- [ ] Market quality gates working (rejecting low-quality markets)
- [ ] Kalshi markets visible and normalized
- [ ] Binance prices streaming in real-time
- [ ] Arbitrage opportunities detected and logged
- [ ] All existing tests still pass
- [ ] New features have >80% test coverage
