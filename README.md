# PolyMind

**AI-Powered Prediction Market Trading Bot**

An autonomous trading system that leverages Claude AI for intelligent decision-making across prediction markets. Features wallet copy-trading, real-time market analysis, and sophisticated risk management.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-black?logo=next.js&logoColor=white)
![Claude AI](https://img.shields.io/badge/Claude_AI-Anthropic-orange)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql&logoColor=white)

## Features

- **AI Decision Engine** - Claude API integration for intelligent trade analysis and execution decisions
- **Wallet Copy Trading** - Monitor and replicate trades from high-performing wallets
- **Multi-Platform Support** - Polymarket, Kalshi, and Binance price feeds
- **Real-Time Dashboard** - Next.js web interface with live position tracking
- **Discord Bot** - Trade alerts and portfolio management via Discord
- **Risk Management** - Configurable limits, drawdown protection, and kill switches
- **CLI Interface** - Full-featured command-line control

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Wallet Watcher │────▶│                 │
└─────────────────┘     │  AI Decision    │     ┌─────────────────┐
                        │     Brain       │────▶│ Execution Engine│
┌─────────────────┐     │  (Claude API)   │     └─────────────────┘
│  Market Scanner │────▶│                 │              │
└─────────────────┘     └─────────────────┘              ▼
                                              ┌─────────────────┐
                                              │ Risk Management │
                                              └─────────────────┘
```

## Tech Stack

**Backend**
- Python 3.11+ with async/await patterns
- FastAPI + Uvicorn for REST API
- SQLAlchemy + AsyncPG for database operations
- Alembic for migrations
- Web3.py for blockchain integration

**Frontend**
- Next.js 14 with App Router
- TypeScript + Tailwind CSS
- Real-time updates via WebSocket

**Infrastructure**
- PostgreSQL + Redis
- Docker Compose for local development
- Supabase for auth & real-time subscriptions

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Cre8toragency/PolyMind-Trading-Bot.git
cd PolyMind-Trading-Bot

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure
docker-compose up -d

# Install Python dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start the bot
polymind start
```

## Configuration

Create a `.env` file with the following:

```env
# AI
ANTHROPIC_API_KEY=your_claude_api_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/polymind

# Markets
POLYMARKET_API_KEY=your_key
KALSHI_API_KEY=your_key

# Optional
DISCORD_BOT_TOKEN=your_token
```

## Dashboard

The web dashboard provides real-time visibility into:
- Active positions and P&L
- Wallet performance metrics
- Trade history and analytics
- Risk exposure monitoring

```bash
cd dashboard
npm install
npm run dev
```

## CLI Commands

```bash
polymind start          # Start the trading bot
polymind status         # Check bot status
polymind wallets list   # List tracked wallets
polymind wallets add    # Add wallet to track
polymind positions      # View open positions
polymind stop           # Graceful shutdown
```

## Risk Management

Built-in safeguards include:
- Maximum daily loss limits
- Per-market exposure caps
- Wallet confidence scoring
- Automatic cooldown after losses
- Emergency kill switch

## Development

```bash
# Run tests
pytest

# Type checking
mypy src

# Linting
ruff check src tests
black src tests --check

# Format code
black src tests
```

## Project Structure

```
├── src/polymind/        # Core trading logic
│   ├── ai/              # Claude AI integration
│   ├── markets/         # Market connectors
│   ├── strategies/      # Trading strategies
│   └── risk/            # Risk management
├── dashboard/           # Next.js web interface
├── bot-service/         # Discord bot
├── migrations/          # Database migrations
├── tests/               # Test suite
└── docs/                # Documentation
```

## License

MIT

---

**Disclaimer:** This software is for educational purposes. Trading prediction markets involves risk. Use at your own discretion.
