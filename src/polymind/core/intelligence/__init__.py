"""Intelligence module for wallet and market analysis."""

__all__ = [
    "WalletMetrics",
    "WalletTracker",
]


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name == "WalletMetrics":
        from polymind.core.intelligence.wallet_metrics import WalletMetrics
        return WalletMetrics
    if name == "WalletTracker":
        from polymind.core.intelligence.wallet_tracker import WalletTracker
        return WalletTracker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
