"""Execution engine module for paper and live trading."""

__all__ = [
    "ExecutionResult",
    "PaperExecutor",
    "SlippageGuard",
    "SlippageExceededError",
    "Order",
    "OrderStatus",
    "OrderManager",
]


def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name in ("ExecutionResult", "PaperExecutor"):
        from polymind.core.execution.paper import ExecutionResult, PaperExecutor
        return {"ExecutionResult": ExecutionResult, "PaperExecutor": PaperExecutor}[name]
    if name in ("SlippageGuard", "SlippageExceededError"):
        from polymind.core.execution.slippage import SlippageGuard, SlippageExceededError
        return {"SlippageGuard": SlippageGuard, "SlippageExceededError": SlippageExceededError}[name]
    if name in ("Order", "OrderStatus"):
        from polymind.core.execution.order import Order, OrderStatus
        return {"Order": Order, "OrderStatus": OrderStatus}[name]
    if name == "OrderManager":
        from polymind.core.execution.manager import OrderManager
        return OrderManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
