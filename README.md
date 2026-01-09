# PolyMind

AI-powered prediction market trading bot for Polymarket.

## Features

- Wallet copy trading
- AI decision brain (Claude API)
- Risk management
- CLI, Web Dashboard, and Discord bot interfaces

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Start infrastructure
docker-compose up -d

# Run the bot
polymind start
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check src tests
black src tests --check

# Type check
mypy src
```
