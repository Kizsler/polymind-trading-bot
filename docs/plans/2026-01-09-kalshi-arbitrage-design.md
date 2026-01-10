# Kalshi Arbitrage Design

## Overview

Use Kalshi prices as a signal source to find mispriced markets on Polymarket and trade them.

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Kalshi    │────▶│  Arbitrage       │────▶│  TradeSignal    │
│   API       │     │  Monitor Service │     │  (to AI Brain)  │
└─────────────┘     └──────────────────┘     └─────────────────┘
                            │
                    ┌───────┴───────┐
                    │ Market        │
                    │ Mappings (DB) │
                    └───────────────┘
```

## Flow

1. ArbitrageMonitorService runs on interval (default: 30 seconds)
2. For each active market mapping in the database:
   - Fetch Kalshi price
   - Fetch Polymarket price
   - Calculate spread
3. If spread > threshold (default: 3%), generate a TradeSignal with type ARBITRAGE
4. Signal goes through existing pipeline: AI Decision → Risk Manager → Paper Executor
5. Manual scans work the same way, just triggered via API

## Direction Logic

- If `kalshi_price > poly_price` → Buy YES on Polymarket (underpriced)
- If `kalshi_price < poly_price` → Buy NO on Polymarket (overpriced)

## Components

### New
- `ArbitrageMonitorService` - Background service in `src/polymind/services/arbitrage.py`

### Existing (to wire up)
- `KalshiClient` - Fetches Kalshi prices
- `MarketNormalizer` - Normalizes prices across platforms
- `ArbitrageDetector` - Calculates spreads and validates opportunities
- `DecisionBrain` - Receives ARBITRAGE type signals

## Config

```python
class ArbitrageSettings:
    enabled: bool = False
    min_spread: float = 0.03  # 3%
    poll_interval: float = 30.0  # seconds
```

## API Endpoints

- `GET /arbitrage/opportunities` - List current opportunities
- `POST /arbitrage/scan` - Trigger manual scan
- `GET /arbitrage/mappings` - List mappings (exists)
- `POST /arbitrage/mappings` - Add mapping (exists)

## Dashboard

- Table of opportunities: Market, Kalshi %, Poly %, Spread, Direction
- "Scan Now" button
- Monitoring status indicator
- Market mapping management
