"""Intelligence module for wallet and market analysis."""

__all__ = [
    "AutoDisableChecker",
    "DisableCheckResult",
    "FilterAction",
    "FilterType",
    "MarketAnalyzer",
    "MarketFilter",
    "MarketFilterManager",
    "MarketQuality",
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
    if name in ("AutoDisableChecker", "DisableCheckResult"):
        from polymind.core.intelligence.auto_disable import (
            AutoDisableChecker,
            DisableCheckResult,
        )
        return {"AutoDisableChecker": AutoDisableChecker, "DisableCheckResult": DisableCheckResult}[name]
    if name in ("MarketAnalyzer", "MarketQuality"):
        from polymind.core.intelligence.market import MarketAnalyzer, MarketQuality
        return {"MarketAnalyzer": MarketAnalyzer, "MarketQuality": MarketQuality}[name]
    if name in ("FilterType", "FilterAction", "MarketFilter", "MarketFilterManager"):
        from polymind.core.intelligence.filters import (
            FilterType,
            FilterAction,
            MarketFilter,
            MarketFilterManager,
        )
        return {
            "FilterType": FilterType,
            "FilterAction": FilterAction,
            "MarketFilter": MarketFilter,
            "MarketFilterManager": MarketFilterManager,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
