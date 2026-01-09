# PolyMind System Design

**Date:** 2026-01-09
**Status:** Approved
**Version:** 1.0

---

## Overview

PolyMind is an AI-powered automated trading bot for prediction markets. The MVP focuses on wallet copy trading on Polymarket, with the AI Decision Brain (Claude API) approving all trades.

## Key Decisions

| Decision | Choice |
|----------|--------|
| Language | Python 3.11+ |
| AI Provider | Claude API |
| MVP Feature | Wallet Copy Trading |
| Data Sources | Polymarket CLOB API + Polygon on-chain |
| Database | PostgreSQL + Redis |
| Deployment | Local first, VPS later |
| Wallet Selection | Manual config, discovery later |
| Interfaces | CLI + Web Dashboard + Discord Bot |
| Trading Mode | Paper trading first |

---

## Project Structure

```
polymind/
├── src/
│   ├── core/                 # Core bot logic
│   │   ├── brain/            # AI Decision Brain (Claude API)
│   │   ├── execution/        # Trade execution engine
│   │   └── risk/             # Risk management layer
│   │
│   ├── data/                 # Data ingestion
│   │   ├── polymarket/       # CLOB API + on-chain monitoring
│   │   ├── kalshi/           # Kalshi API (future)
│   │   └── binance/          # Price feeds (future)
│   │
│   ├── strategies/           # Trading strategies
│   │   ├── copy_trading/     # Wallet copy trading
│   │   ├── sniping/          # Trade sniping (future)
│   │   └── arbitrage/        # Cross-platform arb (future)
│   │
│   ├── storage/              # Database layer
│   │   ├── postgres/         # Persistent storage
│   │   └── redis/            # Real-time cache
│   │
│   ├── interfaces/           # User interfaces
│   │   ├── cli/              # Command-line interface
│   │   ├── dashboard/        # Web dashboard (React/FastAPI)
│   │   └── discord/          # Discord bot
│   │
│   └── utils/                # Shared utilities
│
├── tests/                    # Test suite
├── config/                   # Configuration files
├── docs/                     # Documentation
└── scripts/                  # Helper scripts
```

---

## Core Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Polymarket CLOB │  Polygon Chain  │  (Future: Kalshi, Binance)  │
└────────┬────────┴────────┬────────┴─────────────────────────────┘
         │                 │
         ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    WALLET WATCHER                                │
│  • Monitors configured wallets                                   │
│  • Detects trades (market, side, size, timestamp)               │
│  • Deduplicates CLOB + on-chain signals                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI DECISION BRAIN                             │
│  • Receives trade signals                                        │
│  • Queries wallet performance scores                            │
│  • Queries market liquidity/conditions                          │
│  • Calls Claude API for approve/reject + sizing                 │
│  • Returns: { execute: bool, size: float, confidence: float }   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RISK MANAGEMENT                               │
│  • Validates against hard limits                                │
│  • Checks daily loss, exposure caps                             │
│  • Can override AI decision if limits breached                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTION ENGINE                              │
│  • Paper mode: Log simulated trade                              │
│  • Live mode: Submit to Polymarket                              │
│  • Handle slippage, retries, partial fills                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## AI Decision Brain

**Input Context:**
```python
{
    "signal": {
        "wallet": "0x123...",
        "market_id": "will-btc-hit-50k",
        "side": "YES",
        "size": 500,
        "current_price": 0.65
    },
    "wallet_metrics": {
        "win_rate": 0.72,
        "avg_roi": 1.34,
        "total_trades": 156,
        "recent_performance": "3W-1L last 7 days"
    },
    "market_data": {
        "liquidity": 25000,
        "spread": 0.02,
        "time_to_resolution": "4 hours",
        "volatility": "medium"
    },
    "risk_state": {
        "daily_pnl": -120,
        "open_exposure": 800,
        "max_daily_loss": 500
    }
}
```

**Output:**
```python
{
    "execute": True,
    "size": 250,
    "confidence": 0.78,
    "urgency": "normal",
    "reasoning": "Strong wallet, good liquidity, within risk limits"
}
```

---

## Database Schema

### PostgreSQL

```sql
-- Wallets we're tracking
wallets (
    id, address, alias, enabled,
    created_at, updated_at
)

-- Performance metrics per wallet
wallet_metrics (
    id, wallet_id, win_rate, avg_roi, total_trades,
    total_pnl, last_trade_at, updated_at
)

-- All trades we've detected and our response
trades (
    id, wallet_id, market_id, side, size, price,
    detected_at, source (clob|chain),
    ai_decision, ai_confidence, ai_reasoning,
    executed, executed_size, executed_price,
    paper_mode, pnl, resolved_at
)

-- Market snapshots at decision time
market_snapshots (
    id, trade_id, market_id, liquidity, spread,
    time_to_resolution, captured_at
)

-- Risk events and overrides
risk_events (
    id, event_type, details, triggered_at
)
```

### Redis

```
wallet:{address}:last_trade     # Recent activity
market:{id}:price               # Current prices
market:{id}:liquidity           # Current liquidity
risk:daily_pnl                  # Running daily P&L
risk:open_exposure              # Current exposure
system:mode                     # paper | live | paused
```

---

## User Interfaces

### CLI

```bash
polymind start              # Start the bot
polymind stop               # Stop gracefully
polymind status             # Show current state
polymind wallets list       # List tracked wallets
polymind wallets add 0x...  # Add wallet to track
polymind trades             # Recent trades
polymind mode paper|live    # Switch trading mode
polymind pause              # Emergency pause
```

### Web Dashboard

- **Overview**: Live P&L, open positions, bot status
- **Wallets**: Performance table, enable/disable, add/remove
- **Trades**: Full history with AI reasoning, filters
- **Markets**: Active markets, liquidity, your exposure
- **Settings**: Risk limits, trade sizing, API keys
- **Analytics**: Charts for performance over time

### Discord Bot

Alerts format:
```
🔔 Trade Alert
Wallet: whale.eth copied
Market: "BTC above 50k by Friday"
Side: YES @ $0.65
Size: $250 (paper mode)
AI Confidence: 78%
Reasoning: "Strong wallet, good liquidity"
```

Commands: `/status`, `/pause`, `/resume`, `/trades`, `/pnl`

---

## Risk Management

### Hard Limits

```yaml
risk:
  max_daily_loss: 500
  max_exposure_per_market: 200
  max_exposure_per_wallet: 500
  max_total_exposure: 2000
  max_single_trade: 100
  max_slippage: 0.03
```

### AI-Driven Adjustments

- Reduce trade size by 50% if daily P&L is negative
- Skip trade if wallet's recent performance is declining
- Pause if 3 consecutive losses from same wallet
- Increase urgency if market liquidity is dropping fast

### Safety Features

- Kill switch via CLI, dashboard, or Discord
- Paper mode default
- Cooldown periods after losses
- Rate limiting
- Full audit logging

---

## Tech Stack

### Core
- Python 3.11+
- asyncio

### API & Networking
- httpx (async HTTP)
- websockets
- web3.py (Polygon)
- anthropic (Claude SDK)

### Database
- asyncpg
- redis-py
- sqlalchemy 2.0
- alembic

### Web Dashboard
- FastAPI + uvicorn
- React + Vite + TypeScript
- TailwindCSS
- Recharts

### Discord & CLI
- discord.py
- typer
- rich

### Dev & Testing
- pytest + pytest-asyncio
- ruff
- black
- docker-compose

---

## Implementation Phases

### Phase 1 - Foundation
- Project setup with Python, async structure
- PostgreSQL + Redis with Docker Compose
- Configuration system (YAML-based)
- Basic CLI skeleton

### Phase 2 - Data Layer
- Polymarket CLOB API integration
- Polygon on-chain wallet monitoring
- Data deduplication between sources
- Market data fetching

### Phase 3 - Intelligence
- AI Decision Brain with Claude API
- Wallet performance tracking
- Risk management layer
- Paper trading execution

### Phase 4 - Interfaces
- Full CLI commands
- FastAPI backend for dashboard
- React dashboard frontend
- Discord bot with alerts

### Phase 5 - Polish
- Testing suite
- Error handling & recovery
- Logging & monitoring
- Documentation
