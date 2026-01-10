"""Intelligence module for wallet and market analysis."""

__all__ = [
    "WalletMetrics",
]


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == "WalletMetrics":
        from polymind.core.intelligence.wallet_metrics import WalletMetrics
        return WalletMetrics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
